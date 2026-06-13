"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from microsoft_teams.api import AgenticIdentity, TokenProtocol

from .token_manager import TokenManager


class AppAuthProvider:
    """Provides app and agentic tokens for Teams API clients."""

    def __init__(self, token_manager: TokenManager):
        self._token_manager = token_manager

    async def token(
        self, scope: str, tenant_id: str | None = None, agentic_identity: AgenticIdentity | None = None
    ) -> Optional[TokenProtocol]:
        if agentic_identity is None:
            return await self._token_manager.get_bot_token()
        if tenant_id is None:
            raise ValueError("tenant_id is required to get an agentic token")

        return await self._token_manager.get_agent_user_token(
            tenant_id,
            agentic_identity.agentic_app_id,
            scope,
            agent_user_id=agentic_identity.agentic_user_id,
            caller_name="token",
        )


__all__ = ["AppAuthProvider"]
