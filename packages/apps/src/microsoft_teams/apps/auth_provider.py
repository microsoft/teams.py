"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import AgentUser, TokenProtocol
from microsoft_teams.api.auth.cloud_environment import CloudEnvironment

from .token_manager import TokenManager


class AppAuthProvider:
    """Provides app and agent user tokens for Teams API clients."""

    def __init__(self, token_manager: TokenManager, cloud: CloudEnvironment):
        self._token_manager = token_manager
        self._cloud = cloud

    async def token(self, *, scope: str | None = None, agent_user: AgentUser | None = None) -> TokenProtocol | None:
        if agent_user is None:
            return await self._token_manager.get_app_token(
                scope or self._cloud.bot_scope,
                caller_name="token",
            )

        return await self._token_manager.get_agent_user_token(
            scope or self._cloud.agent_bot_scope,
            agent_user,
            caller_name="token",
        )


__all__ = ["AppAuthProvider"]
