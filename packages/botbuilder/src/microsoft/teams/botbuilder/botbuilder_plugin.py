# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
from logging import Logger
from types import SimpleNamespace
from typing import Annotated, Any, Callable, Optional, TypedDict, Unpack, cast

from fastapi import HTTPException, Request, Response
from microsoft.teams.api import Credentials, TokenProtocol
from microsoft.teams.apps import (
    ActivityEvent,
    DependencyMetadata,
    ErrorEvent,
    EventMetadata,
    HttpPlugin,
    LoggerDependencyOptions,
    Plugin,
)
from microsoft.teams.common import Client

from botbuilder.core import (
    ActivityHandler,
    TurnContext,
)
from botbuilder.integration.aiohttp import (
    CloudAdapter,
    ConfigurationBotFrameworkAuthentication,
)
from botbuilder.schema import Activity

version = importlib.metadata.version("microsoft-teams-botbuilder")


class BotBuilderPluginOptions(TypedDict, total=False):
    """Options for configuring the BotBuilder plugin."""

    skip_auth: bool
    handler: ActivityHandler
    adapter: CloudAdapter


@Plugin(name="http", version=version, description="BotBuilder plugin for Microsoft Bot Framework integration")
class BotBuilderPlugin(HttpPlugin):
    """
    BotBuilder plugin that provides Microsoft Bot Framework integration.
    """

    # Dependency injections
    logger: Annotated[Logger, LoggerDependencyOptions()]
    credentials: Annotated[Optional[Credentials], DependencyMetadata(optional=True)]
    client: Annotated[Client, DependencyMetadata()]

    bot_token: Annotated[Optional[Callable[[], TokenProtocol]], DependencyMetadata(optional=True)]
    graph_token: Annotated[Optional[Callable[[], TokenProtocol]], DependencyMetadata(optional=True)]

    on_error_event: Annotated[Callable[[ErrorEvent], None], EventMetadata(name="error")]
    on_activity_event: Annotated[Callable[[ActivityEvent], None], EventMetadata(name="activity")]

    def __init__(self, **options: Unpack[BotBuilderPluginOptions]):
        """
        Initialize the BotBuilder plugin.

        Args:
            options: Configuration options for the plugin
        """
        self.options = options
        super().__init__(
            app_id=None,
            skip_auth=self.options.get("skip_auth", False),
        )

        self.handler: Optional[ActivityHandler] = self.options.get("handler")
        self.adapter: Optional[CloudAdapter] = self.options.get("adapter")

    async def on_init(self) -> None:
        """Initialize the plugin when the app starts."""
        await super().on_init()

        if not self.adapter:
            # Extract credentials for Bot Framework authentication
            client_id: Optional[str] = None
            client_secret: Optional[str] = None
            tenant_id: Optional[str] = None

            if self.credentials:
                client_id = getattr(self.credentials, "client_id", None)
                client_secret = getattr(self.credentials, "client_secret", None)
                tenant_id = getattr(self.credentials, "tenant_id", None)

            config = SimpleNamespace(
                APP_TYPE="singletenant" if tenant_id else "multitenant",
                APP_ID=client_id,
                APP_PASSWORD=client_secret,
                APP_TENANTID=tenant_id,
            )

            self.adapter = CloudAdapter(ConfigurationBotFrameworkAuthentication(configuration=config))

            self.logger.info("BotBuilder plugin initialized successfully")

    async def on_activity_request(self, request: Request, response: Response) -> Any:
        if not self.adapter:
            raise RuntimeError("plugin not registered")

        try:
            # Parse activity data
            body = await request.json()
            activity_bf = cast(Activity, Activity().deserialize(body))

            # A POST request must contain an Activity
            if not activity_bf.type:
                raise HTTPException(status_code=400, detail="Missing activity type")

            async def logic(turn_context: TurnContext):
                if not turn_context.activity.id:
                    return

                # Handle activity with botframework handler
                if self.handler:
                    await self.handler.on_turn(turn_context)

            # Grab the auth header from the inbound request
            auth_header = request.headers["Authorization"] if "Authorization" in request.headers else ""
            await self.adapter.process_activity(auth_header, activity_bf, logic)

            # Call HTTP plugin to handle activity request
            result = await self._handle_activity_request(request)
            return self._handle_activity_response(response, result)

        except HTTPException:
            raise
        except Exception as err:
            self.logger.error(f"Error processing activity: {err}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(err)) from err
