"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from inspect import isawaitable
from typing import Any, Optional

import requests
from microsoft.teams.api import (
    ClientCredentials,
    Credentials,
    JsonWebToken,
    TokenProtocol,
)
from microsoft.teams.api.auth.credentials import ManagedIdentityCredentials, TokenCredentials
from microsoft.teams.common import ConsoleLogger
from msal import (  # pyright: ignore[reportMissingTypeStubs]
    ConfidentialClientApplication,
    ManagedIdentityClient,
    UserAssignedManagedIdentity,
)

BOT_TOKEN_SCOPE = "https://api.botframework.com/.default"
GRAPH_TOKEN_SCOPE = "https://graph.microsoft.com/.default"
DEFAULT_TENANT_FOR_BOT_TOKEN = "botframework.com"
DEFAULT_TENANT_FOR_GRAPH_TOKEN = "common"
DEFAULT_TOKEN_AUTHORITY = "https://login.microsoftonline.com/{tenant_id}"


class TokenManager:
    """Manages authentication tokens for the Teams application."""

    def __init__(
        self,
        credentials: Optional[Credentials],
        logger: Optional[logging.Logger] = None,
    ):
        self._credentials = credentials

        if not logger:
            self._logger = ConsoleLogger().create_logger("TokenManager")
        else:
            self._logger = logger.getChild("TokenManager")

        self._msal_clients_by_tenantId: dict[str, ConfidentialClientApplication | ManagedIdentityClient] = {}

    async def get_bot_token(self) -> Optional[TokenProtocol]:
        """Refresh the bot authentication token."""
        return await self._get_token(
            BOT_TOKEN_SCOPE, tenant_id=self._resolve_tenant_id(None, DEFAULT_TENANT_FOR_BOT_TOKEN)
        )

    async def get_graph_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        """
        Get or refresh a Graph API token.

        Args:
            tenant_id: If provided, gets a tenant-specific token. Otherwise uses app's default.
            force: Force refresh even if token is not expired

        Returns:
            The graph token or None if not available
        """
        return await self._get_token(
            GRAPH_TOKEN_SCOPE, tenant_id=self._resolve_tenant_id(tenant_id, DEFAULT_TENANT_FOR_GRAPH_TOKEN)
        )

    async def _get_token(
        self, scope: str, tenant_id: str, *, caller_name: str | None = None
    ) -> Optional[TokenProtocol]:
        credentials = self._credentials
        if self._credentials is None:
            if caller_name:
                self._logger.debug(f"No credentials provided for {caller_name}")
            return None
        if isinstance(credentials, (ClientCredentials, ManagedIdentityCredentials)):
            msal_client = self._get_msal_client(tenant_id)

            # Handle different acquire_token_for_client signatures
            if isinstance(msal_client, ManagedIdentityClient):
                # ManagedIdentityClient expects resource as a keyword-only string parameter
                scope = scope.removesuffix("/.default")
                token_res: dict[str, Any] | None = await asyncio.to_thread(
                    lambda: msal_client.acquire_token_for_client(resource=scope)
                )
            else:
                # ConfidentialClientApplication expects scopes as a list
                token_res: dict[str, Any] | None = await asyncio.to_thread(
                    lambda: msal_client.acquire_token_for_client([scope])
                )

            if token_res.get("access_token", None):
                access_token = token_res["access_token"]
                return JsonWebToken(access_token)
            else:
                self._logger.debug(f"TokenRes: {token_res}")
                error = token_res.get("error", "Error retrieving token")
                if not isinstance(error, BaseException):
                    error = ValueError(error)
                error_description = token_res.get("error_description", "Error retrieving token from MSAL")
                self._logger.error(error_description)
                raise error
        elif isinstance(credentials, TokenCredentials):
            token = credentials.token(scope, tenant_id)
            if isawaitable(token):
                access_token = await token
            else:
                access_token = token

            return JsonWebToken(access_token)

    def _get_msal_client(self, tenant_id: str) -> ConfidentialClientApplication | ManagedIdentityClient:
        credentials = self._credentials

        # Check if client already exists in cache
        cached_client = self._msal_clients_by_tenantId.get(tenant_id)
        if cached_client:
            return cached_client

        # Create the appropriate client based on credential type
        if isinstance(credentials, ClientCredentials):
            client: ConfidentialClientApplication | ManagedIdentityClient = ConfidentialClientApplication(
                credentials.client_id,
                client_credential=credentials.client_secret,
                authority=f"https://login.microsoftonline.com/{tenant_id}",
            )
        elif isinstance(credentials, ManagedIdentityCredentials):
            # Create user-assigned managed identity
            managed_identity = UserAssignedManagedIdentity(client_id=credentials.client_id)

            client = ManagedIdentityClient(
                managed_identity,
                http_client=requests.Session(),
            )
        else:
            raise ValueError(f"Unsupported credential type: {type(credentials)}")

        self._msal_clients_by_tenantId[tenant_id] = client
        return client

    def _resolve_tenant_id(self, tenant_id: str | None, default_tenant_id: str):
        return tenant_id or (self._credentials.tenant_id if self._credentials else False) or default_tenant_id
