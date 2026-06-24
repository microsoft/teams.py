"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import AgenticIdentity, TokenProtocol
from microsoft_teams.api.auth.cloud_environment import CloudEnvironment

from .token_manager import TokenManager


class AppAuthProvider:
    """Provides app and agentic tokens for Teams API clients."""

    def __init__(self, token_manager: TokenManager, cloud: CloudEnvironment):
        self._token_manager = token_manager
        self._cloud = cloud

    async def token(
        self, *, scope: str | None = None, agentic_identity: AgenticIdentity | None = None
    ) -> TokenProtocol | None:
        if agentic_identity is None:
            return await self._token_manager.get_app_token(
                scope or self._cloud.bot_scope,
                caller_name="token",
            )

        return await self._token_manager.get_agentic_token(
            scope or self._cloud.agentic_bot_scope,
            agentic_identity,
            caller_name="token",
        )


__all__ = ["AppAuthProvider"]
