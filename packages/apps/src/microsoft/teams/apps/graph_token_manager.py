"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Dict, Optional

from microsoft.teams.api import ApiClient, ClientCredentials, Credentials, JsonWebToken, TokenProtocol


class GraphTokenManager:
    """Simple token manager for Graph API tokens."""

    def __init__(
        self,
        api_client: "ApiClient",
        credentials: Optional["Credentials"],
        logger: Optional[logging.Logger] = None,
    ):
        self._api_client = api_client
        self._credentials = credentials

        if not logger:
            self._logger = logging.getLogger(__name__ + ".GraphTokenManager")
        else:
            self._logger = logger.getChild("GraphTokenManager")

        self._token_cache: Dict[str, TokenProtocol] = {}

    async def get_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """Get a Graph token for the specified tenant."""
        if not self._credentials:
            return None

        if not tenant_id:
            tenant_id = "botframework.com"  # Default tenant ID, assuming multi-tenant app

        # Check cache first
        cached_token = self._token_cache.get(tenant_id)
        if cached_token and not cached_token.is_expired():
            return cached_token

        # Refresh token
        try:
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

            self._logger.debug(f"Refreshed graph token for tenant {tenant_id}")

            return token

        except Exception as e:
            self._logger.error(f"Failed to refresh graph token for {tenant_id}: {e}")
            return None
