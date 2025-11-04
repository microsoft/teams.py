# pyright: reportMissingTypeStubs=false, reportUnknownMemberType=false

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
from logging import Logger
from types import SimpleNamespace
from typing import Annotated, Any, Optional, Unpack, cast

from fastapi import HTTPException, Request, Response
from microsoft.teams.api import Credentials
from microsoft.teams.apps import (
    DependencyMetadata,
    HttpPlugin,
    LoggerDependencyOptions,
    Plugin,
)
from microsoft.teams.apps.http_plugin import HttpPluginOptions

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

# Constants for app types
SINGLE_TENANT = "singletenant"
MULTI_TENANT = "multitenant"


class BotBuilderPluginOptions(HttpPluginOptions, total=False):
    """Options for configuring the BotBuilder plugin."""

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

    def __init__(self, **options: Unpack[BotBuilderPluginOptions]):
        """
        Initialize the BotBuilder plugin.

        Args:
            options: Configuration options for the plugin
        """

        self.handler: Optional[ActivityHandler] = options.get("handler")
        self.adapter: Optional[CloudAdapter] = options.get("adapter")

        super().__init__(**options)

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
                APP_TYPE=SINGLE_TENANT if tenant_id else MULTI_TENANT,
                APP_ID=client_id,
                APP_PASSWORD=client_secret,
                APP_TENANTID=tenant_id,
            )

            bot_framework_auth = ConfigurationBotFrameworkAuthentication(configuration=config)
            self.adapter = CloudAdapter(bot_framework_auth)

            self.logger.debug("BotBuilder plugin initialized successfully")

    async def on_activity_request(self, request: Request, response: Response) -> Any:
        """
        Handles an incoming activity.

        Overrides the base HTTP plugin behavior to:
        1. Process the activity using the Bot Framework adapter/handler.
        2. Then pass the request to the Teams plugin pipeline (_handle_activity_request).

        Returns the final HTTP response.
        """
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

        except HTTPException as http_err:
            self.logger.error(f"HTTP error processing activity: {http_err}", exc_info=True)
            raise
        except Exception as err:
            self.logger.error(f"Error processing activity: {err}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(err)) from err
