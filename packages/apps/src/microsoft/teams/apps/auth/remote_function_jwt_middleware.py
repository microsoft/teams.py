"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, Awaitable, Callable, Dict, List, Optional

from fastapi import HTTPException, Request, Response

from ..contexts import ClientContext
from .token_validator import TokenValidator


def require_fields(fields: Dict[str, Optional[Any]], context: str, logger: Logger) -> None:
    missing: List[str] = [name for name, value in fields.items() if not value]
    if missing:
        message = f"Missing or invalid fields in {context}: {', '.join(missing)}"
        logger.warning(message)
        raise HTTPException(status_code=401, detail=message)


def remote_function_jwt_validation(logger: Logger, entra_token_validator: Optional[TokenValidator]):
    """
    Middleware to validate JWT for remote function calls.
    Args:
        entra_token_validator: TokenValidator instance for Entra ID tokens
        logger: Logger instance

    Returns:
        Middleware function that can be added to FastAPI app
    """

    async def middleware(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Extract auth token
        authorization = request.headers.get("Authorization", "")
        parts = authorization.split(" ")
        auth_token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else ""

        # Validate headers
        require_fields(
            {
                "X-Teams-App-Session-Id": request.headers.get("X-Teams-App-Session-Id"),
                "X-Teams-Page-Id": request.headers.get("X-Teams-Page-Id"),
                "Authorization (Bearer token)": auth_token,
            },
            "header",
            logger,
        )

        if not entra_token_validator:
            raise HTTPException(status_code=500, detail="Token validator not configured")

        # Validate token
        token_payload = await entra_token_validator.validate_token(auth_token)

        # Validate required fields in token
        require_fields(
            {"oid": token_payload.get("oid"), "tid": token_payload.get("tid"), "name": token_payload.get("name")},
            "token payload",
            logger,
        )

        # Build context
        request.state.context = ClientContext(
            app_session_id=request.headers.get("X-Teams-App-Session-Id"),  # type: ignore
            tenant_id=token_payload["tid"],
            user_id=token_payload["oid"],
            user_name=token_payload["name"],
            page_id=request.headers.get("X-Teams-Page-Id"),  # type: ignore
            auth_token=auth_token,  # type: ignore
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
