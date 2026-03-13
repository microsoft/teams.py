"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
from logging import Logger
from types import SimpleNamespace
from typing import Annotated, Any, Callable, Dict, Optional, TypedDict, Unpack, cast

from microsoft_teams.api import Credentials, InvokeResponse
from microsoft_teams.apps import (
    DependencyMetadata,
    EventMetadata,
    HttpServerAdapter,
    LoggerDependencyOptions,
    Plugin,
    PluginBase,
)
from microsoft_teams.apps.events import ActivityEvent, CoreActivity, ErrorEvent
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
    logger: Annotated[Logger, LoggerDependencyOptions()]
    credentials: Annotated[Optional[Credentials], DependencyMetadata(optional=True)]
    http_server_adapter: Annotated[HttpServerAdapter, DependencyMetadata()]

    on_error_event: Annotated[Callable[[ErrorEvent], None], EventMetadata(name="error")]
    on_activity_event: Annotated[Callable[[ActivityEvent], InvokeResponse[Any]], EventMetadata(name="activity")]

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

            self.logger.debug("BotBuilder plugin initialized successfully")

        # Register the activity route via adapter
        self.http_server_adapter.register_route("POST", "/api/messages", self._handle_activity)

    async def _handle_activity(self, request: HttpRequest) -> HttpResponse:
        """
        Pure handler for POST /api/messages.

        Processes via Bot Framework, then passes to the Teams pipeline.
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

            # Process through Teams pipeline
            core_activity = CoreActivity.model_validate(body)
            token = cast(
                Any,
                SimpleNamespace(
                    app_id="",
                    app_display_name="",
                    tenant_id="",
                    service_url=core_activity.service_url or "",
                    from_="azure",
                    from_id="",
                    is_expired=lambda: False,
                ),
            )

            event_result = self.on_activity_event(ActivityEvent(body=core_activity, token=token))
            result: Any = await cast(Any, event_result)

            # Format response
            status_code: int = 200
            resp_body: Any = None
            resp_dict: Dict[str, Any] = {}
            if result is not None and hasattr(result, "model_dump"):
                resp_dict = cast(Dict[str, Any], result.model_dump(exclude_none=True))
            elif isinstance(result, dict):
                resp_dict = cast(Dict[str, Any], result)

            if "status" in resp_dict:
                status_code = int(resp_dict.get("status", 200))
            if "body" in resp_dict:
                resp_body = resp_dict.get("body")

            return HttpResponse(status=status_code, body=resp_body)

        except Exception as err:
            self.logger.error(f"Error processing activity: {err}", exc_info=True)
            return HttpResponse(status=500, body={"detail": str(err)})
