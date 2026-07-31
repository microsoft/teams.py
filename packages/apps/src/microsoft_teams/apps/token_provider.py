"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import AgenticIdentity, TokenProtocol
from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment
from microsoft_teams.api.auth.credentials import AgenticIdentityTokenProviderProtocol

from .token_manager import TokenManager


class AppTokenProvider(AgenticIdentityTokenProviderProtocol):
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

    async def get_agentic_identity_token(
        self,
        scope: str | None,
        agentic_identity: AgenticIdentity,
    ) -> TokenProtocol | None:
        """Acquire a token carrying an agentic identity scope."""
        return await self._token_manager.get_agentic_identity_token(
            scope or self._cloud.agent_bot_scope,
            agentic_identity,
        )


__all__ = ["AppTokenProvider"]
