"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Optional

from microsoft.teams.api import (
    BotTokenClient,
    ClientCredentials,
    Credentials,
    JsonWebToken,
    TokenProtocol,
    UserTokenClient,
)
from microsoft.teams.common import Client, ConsoleLogger, LocalStorage, LocalStorageOptions
from microsoft.teams.common.http.client import ClientOptions


class TokenManager:
    """Manages authentication tokens for the Teams application."""

    def __init__(
        self,
        http_client: Client,
        credentials: Optional[Credentials],
        logger: Optional[logging.Logger] = None,
        default_connection_name: Optional[str] = None,
    ):
        self._bot_token_client = BotTokenClient(http_client.clone())
        self._user_token_client = UserTokenClient(
            http_client.clone(ClientOptions(token=lambda: self.get_bot_token(force=False)))
        )
        self._credentials = credentials
        self._default_connection_name = default_connection_name

        if not logger:
            self._logger = ConsoleLogger().create_logger("TokenManager")
        else:
            self._logger = logger.getChild("TokenManager")

        self._bot_token: Optional[TokenProtocol] = None

        # Key: tenant_id (empty string "" for default app graph token)
        self._graph_tokens: LocalStorage[TokenProtocol] = LocalStorage({}, LocalStorageOptions(max=20000))

    async def get_bot_token(self, force: bool = False) -> Optional[TokenProtocol]:
        """Refresh the bot authentication token."""
        if not self._credentials:
            self._logger.warning("No credentials provided, skipping bot token refresh")
            return None

        if not force and self._bot_token and not self._bot_token.is_expired():
            return self._bot_token

        if self._bot_token:
            self._logger.debug("Refreshing bot token")
        else:
            self._logger.debug("Retrieving bot token")

        token_response = await self._bot_token_client.get(self._credentials)
        self._bot_token = JsonWebToken(token_response.access_token)
        self._logger.debug("Bot token refreshed successfully")
        return self._bot_token

    async def get_graph_token(self, tenant_id: Optional[str] = None, force: bool = False) -> Optional[TokenProtocol]:
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

        response = await self._bot_token_client.get_graph(creds)
        token = JsonWebToken(response.access_token)
        self._graph_tokens.set(key, token)

        self._logger.debug(f"Refreshed graph token tenant_id={tenant_id}")

        return token
