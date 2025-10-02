"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Awaitable, Callable, Optional, cast

from fastapi import HTTPException, Request, Response

from ..contexts import ClientContext
from .token_validator import TokenValidator


def remote_function_jwt_validation(entra_token_validator: Optional[TokenValidator], logger: Logger):
    """
    Middleware to validate JWT for remote function calls.
    Args:
        entra_token_validator: TokenValidator instance for Entra ID tokens
        logger: Logger instance

    Returns:
        Middleware function that can be added to FastAPI app
    """

    async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Extract headers
        app_session_id = request.headers.get("X-Teams-App-Session-Id")
        page_id = request.headers.get("X-Teams-Page-Id")
        authorization = request.headers.get("Authorization", "")
        parts = authorization.split(" ")
        auth_token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else ""

        # Validate token
        token_payload = None
        if entra_token_validator:
            token_payload = await entra_token_validator.validate_token(auth_token)

        if not (page_id and app_session_id and auth_token and token_payload):
            logger.warning("unauthorized")
            raise HTTPException(status_code=401, detail="unauthorized")

        # Build the context
        context = {
            "app_id": token_payload.get("appId"),
            "app_session_id": app_session_id,
            "auth_token": auth_token,
            "channel_id": request.headers.get("X-Teams-Channel-Id"),
            "chat_id": request.headers.get("X-Teams-Chat-Id"),
            "meeting_id": request.headers.get("X-Teams-Meeting-Id"),
            "message_id": request.headers.get("X-Teams-Message-Id"),
            "page_id": page_id,
            "sub_page_id": request.headers.get("X-Teams-Sub-Page-Id"),
            "team_id": request.headers.get("X-Teams-Team-Id"),
            "tenant_id": token_payload.get("tid"),
            "user_id": token_payload.get("oid"),
            "user_name": token_payload.get("name"),
        }
        request.state.context = cast(ClientContext, context)

        return await call_next(request)

    return middleware
