"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from types import SimpleNamespace
from typing import Any, Awaitable, Callable, Dict, Optional, cast

from microsoft_teams.api import Credentials, InvokeResponse, TokenProtocol
from microsoft_teams.api.auth.json_web_token import JsonWebToken
from pydantic import BaseModel

from ..auth import TokenValidator
from ..events import ActivityEvent, CoreActivity
from .adapter import HttpRequest, HttpResponse, HttpServerAdapter

logger = logging.getLogger(__name__)


class HttpServer:
    """
    Core Teams HTTP server. Not a plugin — owned directly by the App.

    Manages an HttpServerAdapter instance and handles JWT validation
    and activity processing for the Teams protocol.
    """

    def __init__(self, adapter: HttpServerAdapter):
        self._adapter = adapter
        self._on_request: Optional[Callable[[ActivityEvent], Awaitable[InvokeResponse[Any]]]] = None
        self._token_validator: Optional[TokenValidator] = None
        self._skip_auth: bool = False
        self._initialized: bool = False

    @property
    def adapter(self) -> HttpServerAdapter:
        """The underlying HttpServerAdapter."""
        return self._adapter

    @property
    def on_request(self) -> Optional[Callable[[ActivityEvent], Awaitable[InvokeResponse[Any]]]]:
        """Callback set by App to process activities."""
        return self._on_request

    @on_request.setter
    def on_request(self, callback: Optional[Callable[[ActivityEvent], Awaitable[InvokeResponse[Any]]]]) -> None:
        self._on_request = callback

    def initialize(
        self,
        credentials: Optional[Credentials] = None,
        skip_auth: bool = False,
    ) -> None:
        """
        Set up JWT validation and register the default POST /api/messages route.

        Args:
            credentials: App credentials for JWT validation.
            skip_auth: Whether to skip JWT validation.
        """
        if self._initialized:
            return

        self._skip_auth = skip_auth

        app_id = getattr(credentials, "client_id", None) if credentials else None
        if app_id and not skip_auth:
            self._token_validator = TokenValidator.for_service(app_id)
            logger.debug("JWT validation enabled for /api/messages")

        self._adapter.register_route("POST", "/api/messages", self.handle_request)
        self._initialized = True

    async def handle_request(self, request: HttpRequest) -> HttpResponse:
        """Handle incoming activity request. Public so plugins (e.g. BotBuilder) can route through SDK auth."""
        try:
            body = request["body"]
            headers = request["headers"]

            # Validate JWT token
            authorization = headers.get("authorization") or headers.get("Authorization") or ""

            if self._token_validator and not self._skip_auth:
                if not authorization.startswith("Bearer "):
                    return HttpResponse(status=401, body={"error": "Unauthorized"})

                raw_token = authorization.removeprefix("Bearer ")
                service_url = cast(Optional[str], body.get("serviceUrl"))

                try:
                    await self._token_validator.validate_token(raw_token, service_url)
                except Exception as e:
                    logger.warning(f"JWT token validation failed: {e}")
                    return HttpResponse(status=401, body={"error": "Unauthorized"})

                token: TokenProtocol = cast(TokenProtocol, JsonWebToken(value=raw_token))
            else:
                # No auth — use a default token
                service_url = cast(Optional[str], body.get("serviceUrl"))
                token = cast(
                    TokenProtocol,
                    SimpleNamespace(
                        app_id="",
                        app_display_name="",
                        tenant_id="",
                        service_url=service_url or "",
                        from_="azure",
                        from_id="",
                        is_expired=lambda: False,
                    ),
                )

            core_activity = CoreActivity.model_validate(body)
            activity_type = core_activity.type or "unknown"
            activity_id = core_activity.id or "unknown"
            logger.debug(f"Received activity: {activity_type} (ID: {activity_id})")

            # Process the activity via the App callback
            result = await self._process_activity(core_activity, token)
            return self._format_response(result)
        except Exception as e:
            logger.exception(str(e))
            return HttpResponse(status=500, body={"error": "Internal server error"})

    async def _process_activity(self, core_activity: CoreActivity, token: TokenProtocol) -> InvokeResponse[Any]:
        """Process an activity via the registered on_request callback."""
        event = ActivityEvent(body=core_activity, token=token)
        if self._on_request:
            return await self._on_request(event)

        logger.warning("No on_request handler registered")
        return InvokeResponse(status=500)

    def _format_response(self, result: Any) -> HttpResponse:
        """Format an InvokeResponse into an HttpResponse."""
        status_code: int = 200
        body: Optional[Any] = None

        resp_dict: Optional[Dict[str, Any]] = None
        if isinstance(result, dict):
            resp_dict = cast(Dict[str, Any], result)
        elif isinstance(result, BaseModel):
            resp_dict = result.model_dump(exclude_none=True)

        if resp_dict and "status" in resp_dict:
            status_code = resp_dict.get("status", 200)

        if resp_dict and "body" in resp_dict:
            body = resp_dict.get("body")

        if body is not None:
            return HttpResponse(status=status_code, body=body)
        return HttpResponse(status=status_code, body=None)
