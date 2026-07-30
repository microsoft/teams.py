"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import AgenticUser, TokenProtocol
from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment
from microsoft_teams.api.auth.credentials import (
    AgenticAppInstanceTokenProviderProtocol,
    AgenticUserTokenProviderProtocol,
)

from .token_manager import TokenManager


class AppTokenProvider(AgenticUserTokenProviderProtocol, AgenticAppInstanceTokenProviderProtocol):
    """Public token source backed by the credentials configured on an App."""

    def __init__(self, token_manager: TokenManager, cloud: CloudEnvironment = PUBLIC):
        self._token_manager = token_manager
        self._cloud = cloud

    async def get_app_token(
        self,
        scope: str | None = None,
        tenant_id: str | None = None,
    ) -> TokenProtocol | None:
        """Acquire an app-only token."""
        return await self._token_manager.get_app_token(scope or self._cloud.bot_scope, tenant_id)

    async def get_agentic_user_token(
        self,
        scope: str | None,
        agentic_user: AgenticUser,
    ) -> TokenProtocol | None:
        """Acquire a token carrying an Agentic User identity."""
        return await self._token_manager.get_agentic_user_token(
            scope or self._cloud.agent_bot_scope,
            agentic_user,
        )

    async def get_agentic_app_instance_token(
        self,
        scope: str,
        agentic_app_instance_id: str,
        tenant_id: str | None = None,
    ) -> TokenProtocol | None:
        """Acquire an app-only token for an Agentic App Instance."""
        return await self._token_manager.get_agentic_app_instance_token(
            scope,
            agentic_app_instance_id,
            tenant_id,
        )


__all__ = ["AppTokenProvider"]
