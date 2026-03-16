"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Dict, Optional

from ..contexts import ClientContext
from .token_validator import TokenValidator

logger = logging.getLogger(__name__)


def _require_fields(fields: Dict[str, Optional[str]], context: str) -> Optional[str]:
    """Validate required fields are present. Returns error message if any are missing, None otherwise."""
    missing = [name for name, value in fields.items() if not value]
    if missing:
        message = f"Missing or invalid fields in {context}: {', '.join(missing)}"
        logger.warning(message)
        return message
    return None


async def validate_remote_function_request(
    headers: Dict[str, str],
    entra_token_validator: Optional[TokenValidator],
) -> tuple[Optional[ClientContext], Optional[str]]:
    """
    Validate JWT and extract client context from request headers for remote function calls.

    Args:
        headers: Request headers dict.
        entra_token_validator: TokenValidator instance for Entra ID tokens.

    Returns:
        Tuple of (ClientContext, None) on success or (None, error_message) on failure.
    """
    # Extract auth token
    authorization = headers.get("Authorization") or headers.get("authorization") or ""
    parts = authorization.split(" ")
    auth_token = parts[1] if len(parts) == 2 and parts[0].lower() == "bearer" else ""

    # Validate headers
    error = _require_fields(
        {
            "X-Teams-App-Session-Id": headers.get("X-Teams-App-Session-Id") or headers.get("x-teams-app-session-id"),
            "X-Teams-Page-Id": headers.get("X-Teams-Page-Id") or headers.get("x-teams-page-id"),
            "Authorization (Bearer token)": auth_token,
        },
        "header",
    )
    if error:
        return None, error

    if not entra_token_validator:
        return None, "Token validator not configured"

    # Validate token
    token_payload = await entra_token_validator.validate_token(auth_token)

    # Validate required fields in token
    error = _require_fields(
        {"oid": token_payload.get("oid"), "tid": token_payload.get("tid"), "name": token_payload.get("name")},
        "token payload",
    )
    if error:
        return None, error

    def _h(name: str) -> str:
        """Get header value case-insensitively."""
        return headers.get(name) or headers.get(name.lower()) or ""

    context = ClientContext(
        app_session_id=_h("X-Teams-App-Session-Id"),
        tenant_id=token_payload["tid"],
        user_id=token_payload["oid"],
        user_name=token_payload["name"],
        page_id=_h("X-Teams-Page-Id"),
        auth_token=auth_token,
        app_id=token_payload.get("appId"),
        channel_id=_h("X-Teams-Channel-Id") or None,
        chat_id=_h("X-Teams-Chat-Id") or None,
        meeting_id=_h("X-Teams-Meeting-Id") or None,
        message_id=_h("X-Teams-Message-Id") or None,
        sub_page_id=_h("X-Teams-Sub-Page-Id") or None,
        team_id=_h("X-Teams-Team-Id") or None,
    )

    return context, None
