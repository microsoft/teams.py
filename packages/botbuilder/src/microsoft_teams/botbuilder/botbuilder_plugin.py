"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
import logging
from types import SimpleNamespace
from typing import Annotated, Optional, TypedDict, Unpack, cast

from microsoft_teams.api import Credentials
from microsoft_teams.apps import (
    DependencyMetadata,
    HttpServer,
    Plugin,
    PluginBase,
)
from microsoft_teams.apps.http import HttpRequest, HttpResponse

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

logger = logging.getLogger(__name__)

# Constants for app types
SINGLE_TENANT = "singletenant"
MULTI_TENANT = "multitenant"


class BotBuilderPluginOptions(TypedDict, total=False):
    """Options for configuring the BotBuilder plugin."""

    handler: ActivityHandler
    adapter: CloudAdapter


@Plugin(name="botbuilder", version=version, description="BotBuilder plugin for Microsoft Bot Framework integration")
class BotBuilderPlugin(PluginBase):
    """
    BotBuilder plugin that provides Microsoft Bot Framework integration.
    """

    # Dependency injections
    credentials: Annotated[Optional[Credentials], DependencyMetadata(optional=True)]
    http_server: Annotated[HttpServer, DependencyMetadata()]

    def __init__(self, **options: Unpack[BotBuilderPluginOptions]):
        """
        Initialize the BotBuilder plugin.

        Args:
            options: Configuration options for the plugin
        """
        super().__init__()
        self.handler: Optional[ActivityHandler] = options.get("handler")
        self.adapter: Optional[CloudAdapter] = options.get("adapter")

    async def on_init(self) -> None:
        """Initialize the plugin when the app starts."""
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

            logger.debug("BotBuilder plugin initialized successfully")

        # Register the activity route via adapter (bypasses HttpServer's default /api/messages)
        self.http_server.adapter.register_route("POST", "/api/messages", self._handle_activity)

    async def _handle_activity(self, request: HttpRequest) -> HttpResponse:
        """
        Handler for POST /api/messages.

        Runs Bot Framework CloudAdapter auth + handler first,
        then routes through HttpServer.handle_request for SDK-level JWT validation and pipeline.
        """
        if not self.adapter:
            raise RuntimeError("plugin not registered")

        body = request["body"]
        headers = request["headers"]

        try:
            # Parse activity from body
            activity_bf = cast(Activity, Activity().deserialize(body))

            if not activity_bf.type:
                return HttpResponse(status=400, body={"detail": "Missing activity type"})

            async def logic(turn_context: TurnContext) -> None:
                if not turn_context.activity.id:
                    return
                # Handle activity with botframework handler
                if self.handler:
                    await self.handler.on_turn(turn_context)

            # Grab the auth header from the inbound request
            auth_header = headers.get("authorization") or headers.get("Authorization") or ""
            await self.adapter.process_activity(auth_header, activity_bf, logic)

            # Route through HttpServer for SDK auth + Teams pipeline
            return await self.http_server.handle_request(request)

        except Exception as err:
            logger.error(f"Error processing activity: {err}", exc_info=True)
            return HttpResponse(status=500, body={"detail": str(err)})
