"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Awaitable, Callable

from fastapi import HTTPException, Request, Response

from ..contexts import ClientContext
from .token_validator import TokenValidator


def remote_function_jwt_validation(entra_token_validator: TokenValidator, logger: Logger):
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

        token_payload = await entra_token_validator.validate_token(auth_token)

        if not (page_id and app_session_id and auth_token and token_payload):
            logger.warning("invalid request headers (X-Teams-App-Session-Id, X-Teams-Page-Id) or unauthorized token")
            raise HTTPException(
                status_code=401,
                detail="invalid request headers (X-Teams-App-Session-Id, X-Teams-Page-Id) or unauthorized token",
            )

        # Extract token payload options
        oid = token_payload.get("oid")
        tid = token_payload.get("tid")
        name = token_payload.get("name")

        if not (oid and tid and name):
            logger.warning("invalid token payload")
            raise HTTPException(status_code=401, detail="invalid token payload")

        # Build the context
        request.state.context = ClientContext(
            app_session_id=app_session_id,
            tenant_id=tid,
            user_id=oid,
            user_name=name,
            page_id=page_id,
            auth_token=auth_token,
            app_id=token_payload.get("appId"),
            channel_id=request.headers.get("X-Teams-Channel-Id"),
            chat_id=request.headers.get("X-Teams-Chat-Id"),
            meeting_id=request.headers.get("X-Teams-Meeting-Id"),
            message_id=request.headers.get("X-Teams-Message-Id"),
            sub_page_id=request.headers.get("X-Teams-Sub-Page-Id"),
            team_id=request.headers.get("X-Teams-Team-Id"),
        )

        return await call_next(request)

    return middleware
