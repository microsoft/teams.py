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
from microsoft.teams.api.auth.credentials import (
    FederatedIdentityCredentials,
    ManagedIdentityCredentials,
    TokenCredentials,
)
from microsoft.teams.common import ConsoleLogger
from msal import (
    ConfidentialClientApplication,
    ManagedIdentityClient,
    SystemAssignedManagedIdentity,
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

        self._confidential_clients_by_tenant: dict[str, ConfidentialClientApplication] = {}
        self._managed_identity_client: Optional[ManagedIdentityClient] = None

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
        if isinstance(credentials, ClientCredentials):
            return await self._get_token_with_client_credentials(credentials, scope, tenant_id)
        elif isinstance(credentials, ManagedIdentityCredentials):
            return await self._get_token_with_managed_identity(credentials, scope)
        elif isinstance(credentials, FederatedIdentityCredentials):
            return await self._get_token_with_federated_identity(credentials, scope, tenant_id)
        elif isinstance(credentials, TokenCredentials):
            return await self._get_token_with_token_provider(credentials, scope, tenant_id)

        return None

    async def _get_token_with_client_credentials(
        self,
        credentials: ClientCredentials,
        scope: str,
        tenant_id: str,
    ) -> TokenProtocol:
        """Get token using ClientCredentials (client secret)."""
        confidential_client = self._get_confidential_client(credentials, tenant_id)

        # ConfidentialClientApplication expects scopes as a list
        token_res: dict[str, Any] = await asyncio.to_thread(
            lambda: confidential_client.acquire_token_for_client([scope])
        )

        return self._handle_token_response(token_res)

    async def _get_token_with_managed_identity(
        self,
        credentials: ManagedIdentityCredentials,
        scope: str,
    ) -> TokenProtocol:
        """Get token using ManagedIdentityCredentials (direct, no federation)."""
        mi_client = self._get_managed_identity_client(credentials)

        # ManagedIdentityClient expects resource as a keyword-only string parameter
        resource = scope.removesuffix("/.default")
        token_res: dict[str, Any] = await asyncio.to_thread(
            lambda: mi_client.acquire_token_for_client(resource=resource)
        )

        return self._handle_token_response(token_res)

    async def _get_token_with_federated_identity(
        self,
        credentials: FederatedIdentityCredentials,
        scope: str,
        tenant_id: str,
    ) -> TokenProtocol:
        """Get token using Federated Identity Credentials (two-step flow)."""

        # Step 1: Get MI token from api://AzureADTokenExchange
        mi_token = await self._acquire_managed_identity_token(credentials)

        # Step 2: Use MI token as client_assertion to get final access token
        confidential_client = ConfidentialClientApplication(
            credentials.client_id,
            client_credential={"client_assertion": mi_token},
            authority=DEFAULT_TOKEN_AUTHORITY.format(tenant_id=tenant_id),
        )

        token_res: dict[str, Any] = await asyncio.to_thread(
            lambda: confidential_client.acquire_token_for_client([scope])
        )

        return self._handle_token_response(token_res, error_prefix="FIC Step 2 failed")

    async def _acquire_managed_identity_token(self, credentials: FederatedIdentityCredentials) -> str:
        """Acquire managed identity token for federated identity credentials."""
        # Use shared method to get or create the managed identity client
        mi_client = self._get_managed_identity_client(credentials)

        mi_token_res: dict[str, Any] = await asyncio.to_thread(
            lambda: mi_client.acquire_token_for_client(resource="api://AzureADTokenExchange")
        )

        if not mi_token_res.get("access_token"):
            self._logger.error("FIC Step 1 failed: Could not acquire MI token")
            error = mi_token_res.get("error", ValueError("Error retrieving MI token"))
            if not isinstance(error, BaseException):
                error = ValueError(error)
            raise error

        return mi_token_res["access_token"]

    async def _get_token_with_token_provider(
        self,
        credentials: TokenCredentials,
        scope: str,
        tenant_id: str,
    ) -> TokenProtocol:
        """Get token using custom token provider function."""
        token = credentials.token(scope, tenant_id)

        if isawaitable(token):
            access_token = await token
        else:
            access_token = token

        return JsonWebToken(access_token)

    def _handle_token_response(self, token_res: dict[str, Any], error_prefix: str = "") -> TokenProtocol:
        """Handle token response from MSAL client."""
        if token_res.get("access_token", None):
            access_token = token_res["access_token"]
            return JsonWebToken(access_token)
        else:
            error_msg = f"{error_prefix}: " if error_prefix else ""
            self._logger.error(f"{error_msg}Could not acquire access token")
            self._logger.debug(f"TokenRes: {token_res}")

            error = token_res.get("error", "Error retrieving token")
            if not isinstance(error, BaseException):
                error = ValueError(error)

            error_description = token_res.get("error_description", "Error retrieving token from MSAL")
            self._logger.error(error_description)
            raise error

    def _get_confidential_client(self, credentials: ClientCredentials, tenant_id: str) -> ConfidentialClientApplication:
        """Get or create ConfidentialClientApplication for ClientCredentials."""
        # Check if client already exists in cache
        cached_client = self._confidential_clients_by_tenant.get(tenant_id)
        if cached_client:
            return cached_client

        client: ConfidentialClientApplication = ConfidentialClientApplication(
            credentials.client_id,
            client_credential=credentials.client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )
        self._confidential_clients_by_tenant[tenant_id] = client
        return client

    def _get_managed_identity_client(
        self, credentials: ManagedIdentityCredentials | FederatedIdentityCredentials
    ) -> ManagedIdentityClient:
        """Get or create ManagedIdentityClient for ManagedIdentityCredentials or FederatedIdentityCredentials."""
        # Check if client already exists in cache

        # ManagedIdentityClient is tenant-agnostic, cache single instance
        if self._managed_identity_client:
            return self._managed_identity_client

        # Determine managed identity type
        if isinstance(credentials, FederatedIdentityCredentials):
            if credentials.managed_identity_type == "system":
                managed_identity = SystemAssignedManagedIdentity()
            else:  # "user"
                mi_client_id = credentials.managed_identity_client_id or credentials.client_id
                managed_identity = UserAssignedManagedIdentity(client_id=mi_client_id)
        else:  # ManagedIdentityCredentials
            # ManagedIdentityCredentials only supports user-assigned
            managed_identity = UserAssignedManagedIdentity(client_id=credentials.client_id)

        self._managed_identity_client = ManagedIdentityClient(
            managed_identity,
            http_client=requests.Session(),
        )
        return self._managed_identity_client

    def _resolve_tenant_id(self, tenant_id: str | None, default_tenant_id: str):
        return tenant_id or (self._credentials.tenant_id if self._credentials else False) or default_tenant_id
