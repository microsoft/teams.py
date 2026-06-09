"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import os
from types import SimpleNamespace
from typing import Optional, TypedDict, Unpack, cast

from microsoft_teams.api import Credentials
from microsoft_teams.apps.http import (
    FastAPIAdapter,
    HttpMethod,
    HttpRequest,
    HttpResponse,
    HttpRouteHandler,
    HttpServerAdapter,
)

from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.integration.aiohttp import CloudAdapter, ConfigurationBotFrameworkAuthentication
from botbuilder.schema import Activity

logger = logging.getLogger(__name__)

SINGLE_TENANT = "singletenant"
MULTI_TENANT = "multitenant"
NOT_IMPLEMENTED = 501


class BotBuilderAdapterOptions(TypedDict, total=False):
    """Options for configuring the BotBuilder HTTP adapter."""

    handler: ActivityHandler
    cloud_adapter: CloudAdapter
    http_server_adapter: HttpServerAdapter
    credentials: Credentials


class BotBuilderAdapter:
    """HTTP server adapter that runs BotBuilder before the Teams SDK handler."""

    def __init__(self, **options: Unpack[BotBuilderAdapterOptions]):
        self.handler: Optional[ActivityHandler] = options.get("handler")
        self.cloud_adapter: CloudAdapter = options.get("cloud_adapter") or self._create_cloud_adapter(
            options.get("credentials")
        )
        self.http_server_adapter: HttpServerAdapter = options.get("http_server_adapter") or FastAPIAdapter()

    def register_route(self, method: HttpMethod, path: str, handler: HttpRouteHandler) -> None:
        if method != "POST":
            self.http_server_adapter.register_route(method, path, handler)
            return

        async def botbuilder_handler(request: HttpRequest) -> HttpResponse:
            return await self._handle_request(request, handler)

        self.http_server_adapter.register_route(method, path, botbuilder_handler)

    def serve_static(self, path: str, directory: str) -> None:
        self.http_server_adapter.serve_static(path, directory)

    async def start(self, port: int) -> None:
        await self.http_server_adapter.start(port)

    async def stop(self) -> None:
        await self.http_server_adapter.stop()

    def _create_cloud_adapter(self, credentials: Optional[Credentials] = None) -> CloudAdapter:
        client_id = (
            self._credential_value(credentials, "client_id") or os.getenv("MicrosoftAppId") or os.getenv("CLIENT_ID")
        )
        client_secret = (
            self._credential_value(credentials, "client_secret")
            or os.getenv("MicrosoftAppPassword")
            or os.getenv("CLIENT_SECRET")
        )
        tenant_id = (
            self._credential_value(credentials, "tenant_id")
            or os.getenv("MicrosoftAppTenantId")
            or os.getenv("TENANT_ID")
        )
        app_type = os.getenv("MicrosoftAppType") or (SINGLE_TENANT if tenant_id else MULTI_TENANT)

        if not client_id:
            raise ValueError(
                "BotBuilderAdapter requires credentials when cloud_adapter is not provided. "
                "Pass credentials, pass cloud_adapter, or set MicrosoftAppId/MicrosoftAppPassword "
                "or CLIENT_ID/CLIENT_SECRET environment variables."
            )

        config = SimpleNamespace(
            APP_TYPE=app_type,
            APP_ID=client_id,
            APP_PASSWORD=client_secret,
            APP_TENANTID=tenant_id,
        )
        return CloudAdapter(ConfigurationBotFrameworkAuthentication(configuration=config))

    def _credential_value(self, credentials: Optional[Credentials], name: str) -> Optional[str]:
        value = getattr(credentials, name, None) if credentials else None
        return cast(Optional[str], value)

    async def _handle_request(self, request: HttpRequest, teams_handler: HttpRouteHandler) -> HttpResponse:
        body = request["body"]
        if not isinstance(body.get("type"), str):
            return await teams_handler(request)

        try:
            activity = cast(Activity, Activity().deserialize(body))
            if not activity.type:
                return await teams_handler(request)

            async def logic(turn_context: TurnContext) -> None:
                if not turn_context.activity.id:
                    return
                if self.handler:
                    await self.handler.on_turn(turn_context)

            invoke_response = await self.cloud_adapter.process_activity(
                self._auth_header(request["headers"]),
                activity,
                logic,
            )

            if (
                body.get("type") == "invoke"
                and invoke_response
                and getattr(invoke_response, "status", None) != NOT_IMPLEMENTED
            ):
                return HttpResponse(
                    status=getattr(invoke_response, "status", 200) or 200,
                    body=getattr(invoke_response, "body", None),
                )

            return await teams_handler(request)
        except Exception:
            logger.exception("Error processing activity")
            return HttpResponse(status=500, body={"error": "Internal server error"})

    def _auth_header(self, headers: dict[str, str]) -> str:
        return headers.get("authorization") or headers.get("Authorization") or ""
