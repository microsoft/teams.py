"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Optional

from microsoft.teams.api import ChannelID, ClientCredentials
from microsoft.teams.api.auth.credentials import Credentials
from microsoft.teams.api.auth.json_web_token import JsonWebToken
from microsoft.teams.api.auth.token import TokenProtocol
from microsoft.teams.api.clients.api_client import ApiClient
from microsoft.teams.api.clients.user.params import GetUserTokenParams
from microsoft.teams.common.logging.console import ConsoleLogger
from microsoft.teams.common.storage.local_storage import LocalStorage, LocalStorageOptions


class TokenManager:
    """Manages authentication tokens for the Teams application."""

    def __init__(
        self,
        api_client: ApiClient,
        credentials: Optional[Credentials],
        logger: Optional[logging.Logger] = None,
        default_connection_name: Optional[str] = None,
    ):
        self._api_client = api_client
        self._credentials = credentials
        self._default_connection_name = default_connection_name

        if not logger:
            self._logger = ConsoleLogger().create_logger("TokenManager")
        else:
            self._logger = logger.getChild("TokenManager")

        self._bot_token: Optional[TokenProtocol] = None

        # Key: tenant_id (empty string "" for default app graph token)
        self._graph_tokens: LocalStorage[TokenProtocol] = LocalStorage({}, LocalStorageOptions(max=20000))

    @property
    def bot_token(self):
        return self._bot_token

    def get_tenant_graph_token(self, tenant_id: str | None):
        """
        Returns the graph token for a given tenant id.
        """
        return self._graph_tokens.get(tenant_id or "")

    async def refresh_bot_token(self, force: bool = False) -> Optional[TokenProtocol]:
        """Refresh the bot authentication token."""
        if not self._credentials:
            self._logger.warning("No credentials provided, skipping bot token refresh")
            return None

        if not force and self._bot_token and not self._bot_token.is_expired():
            return self._bot_token

        if self._bot_token:
            self._logger.debug("Refreshing bot token")

        token_response = await self._api_client.bots.token.get(self._credentials)
        self._bot_token = JsonWebToken(token_response.access_token)
        self._logger.debug("Bot token refreshed successfully")
        return self._bot_token

    async def get_or_refresh_graph_token(
        self, tenant_id: Optional[str] = None, force: bool = False
    ) -> Optional[TokenProtocol]:
        """
        Get or refresh a Graph API token.

        Args:
            tenant_id: If provided, gets a tenant-specific token. Otherwise uses app's default.
            force: Force refresh even if token is not expired

        Returns:
            The graph token or None if not available
        """
        if not self._credentials:
            self._logger.debug("No credentials provided for graph token refresh")
            return None

        # Use empty string as key for default graph token
        key = tenant_id or ""

        cached = self._graph_tokens.get(key)
        if not force and cached and not cached.is_expired():
            return cached

        creds = self._credentials
        if tenant_id and isinstance(self._credentials, ClientCredentials):
            creds = ClientCredentials(
                client_id=self._credentials.client_id,
                client_secret=self._credentials.client_secret,
                tenant_id=tenant_id,
            )

        response = await self._api_client.bots.token.get_graph(creds)
        token = JsonWebToken(response.access_token)
        self._graph_tokens.set(key, token)

        self._logger.debug(f"Refreshed graph token tenant_id={tenant_id}")

        return token

    async def get_user_token(self, channel_id: ChannelID, user_id: str) -> Optional[str]:
        """
        Get a user token for the specified channel and user.

        Args:
            channel_id: The channel ID
            user_id: The user ID

        Returns:
            The user token or None if not available
        """
        if not self._default_connection_name:
            self._logger.warning("No default connection name configured, cannot get user token")
            return None

        response = await self._api_client.users.token.get(
            GetUserTokenParams(
                channel_id=channel_id,
                user_id=user_id,
                connection_name=self._default_connection_name,
            )
        )
        return response.token
