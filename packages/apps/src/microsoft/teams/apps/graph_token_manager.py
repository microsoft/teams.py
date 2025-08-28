"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import TYPE_CHECKING, Dict, Optional

from microsoft.teams.api import JsonWebToken, TokenProtocol

if TYPE_CHECKING:
    from microsoft.teams.api import ApiClient, Credentials


class GraphTokenManager:
    """Simple token manager for Graph API tokens."""

    def __init__(
        self,
        api_client: "ApiClient",
        credentials: Optional["Credentials"],
        logger: Optional[Logger] = None,
    ):
        self._api_client = api_client
        self._credentials = credentials
        self._logger = logger
        self._token_cache: Dict[str, TokenProtocol] = {}

    async def get_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Get a Graph token for the specified tenant."""
        if not tenant_id or not self._credentials:
            return None

        # Check cache first
        cached_token = self._token_cache.get(tenant_id)
        if cached_token and not cached_token.is_expired():
            return cached_token

        # Refresh token
        try:
            from microsoft.teams.api import ClientCredentials

            tenant_credentials = self._credentials
            if isinstance(self._credentials, ClientCredentials):
                tenant_credentials = ClientCredentials(
                    client_id=self._credentials.client_id,
                    client_secret=self._credentials.client_secret,
                    tenant_id=tenant_id,
                )

            response = await self._api_client.bots.token.get_graph(tenant_credentials)
            token = JsonWebToken(response.access_token)
            self._token_cache[tenant_id] = token

            if self._logger:
                self._logger.debug(f"Refreshed graph token for tenant {tenant_id}")

            return token

        except Exception as e:
            if self._logger:
                self._logger.error(f"Failed to refresh graph token for {tenant_id}: {e}")
            return None
