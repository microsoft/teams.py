"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from inspect import Parameter, isawaitable, signature
from typing import Any, Awaitable, Callable, Optional, cast

import requests
from microsoft_teams.api import (
    AgenticIdentity,
    ClientCredentials,
    Credentials,
    JsonWebToken,
    TokenProtocol,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment
from microsoft_teams.api.auth.credentials import (
    FederatedIdentityCredentials,
    ManagedIdentityCredentials,
    TokenCredentials,
)
from msal import (
    ConfidentialClientApplication,
    ManagedIdentityClient,
    SystemAssignedManagedIdentity,
    UserAssignedManagedIdentity,
)

DEFAULT_TENANT_FOR_GRAPH_TOKEN = "common"
TOKEN_EXCHANGE_SCOPE = "api://AzureADTokenExchange/.default"
AGENT_BOT_API_SCOPE = "https://botapi.skype.com/.default"

logger = logging.getLogger(__name__)


class TokenManager:
    """Manages authentication tokens for the Teams application."""

    def __init__(
        self,
        credentials: Optional[Credentials],
        cloud: Optional[CloudEnvironment] = None,
    ):
        self._credentials = credentials
        self._cloud = cloud or PUBLIC
        self._confidential_clients_by_tenant: dict[str, ConfidentialClientApplication] = {}
        self._federated_identity_clients_by_tenant: dict[str, ConfidentialClientApplication] = {}
        self._agent_identity_clients_by_tenant_and_app_id: dict[tuple[str, str], ConfidentialClientApplication] = {}
        self._managed_identity_client: Optional[ManagedIdentityClient] = None

    async def get_bot_token(self) -> Optional[TokenProtocol]:
        """Refresh the bot authentication token."""
        return await self._get_token(
            self._cloud.bot_scope, tenant_id=self._resolve_tenant_id(None, self._cloud.login_tenant)
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
            self._cloud.graph_scope, tenant_id=self._resolve_tenant_id(tenant_id, DEFAULT_TENANT_FOR_GRAPH_TOKEN)
        )

    async def get_agent_bot_token(
        self,
        tenant_id: str,
        agent_identity_app_id: str,
        *,
        agent_user_id: str | None = None,
        agent_user_upn: str | None = None,
        caller_name: str | None = None,
    ) -> Optional[TokenProtocol]:
        """Get a Teams bot API token for an agent identity acting through its agent user."""
        return await self.get_agent_user_token(
            tenant_id,
            agent_identity_app_id,
            AGENT_BOT_API_SCOPE,
            agent_user_id=agent_user_id,
            agent_user_upn=agent_user_upn,
            caller_name=caller_name,
        )

    async def get_agent_user_token(
        self,
        tenant_id: str,
        agent_identity_app_id: str,
        scope: str,
        *,
        agent_user_id: str | None = None,
        agent_user_upn: str | None = None,
        caller_name: str | None = None,
    ) -> Optional[TokenProtocol]:
        """Get a resource token for an agent identity acting through its agent user."""
        if not agent_user_id and not agent_user_upn:
            raise ValueError("Either agent_user_id or agent_user_upn must be provided")
        if agent_user_id and agent_user_upn:
            raise ValueError("agent_user_id and agent_user_upn are mutually exclusive")
        if self._credentials is None:
            if caller_name:
                logger.debug(f"No credentials provided for {caller_name}")
            return None

        credentials = self._credentials
        agentic_identity = AgenticIdentity(
            agentic_app_id=agent_identity_app_id,
            agentic_user_id=agent_user_id or agent_user_upn or "",
            tenant_id=tenant_id,
        )
        if isinstance(credentials, TokenCredentials):
            return await self._get_token_with_token_provider(credentials, scope, tenant_id, agentic_identity)

        if not isinstance(credentials, ClientCredentials):
            raise ValueError("Agent user tokens require ClientCredentials")
        confidential_client = self._get_confidential_client(credentials, tenant_id)

        def get_t1_assertion(_context: dict[str, Any]) -> str:
            t1_raw: dict[str, Any] = confidential_client.acquire_token_for_client(
                [TOKEN_EXCHANGE_SCOPE], fmi_path=agent_identity_app_id
            )
            return self._get_access_token_or_raise(t1_raw, "Agent token exchange step 1 failed")

        # The agent identity app needs its own MSAL client. It uses the Federated Managed
        # Identity assertion from step 1 as its client assertion for the next exchanges.
        t2_confidential_client = self._get_agent_identity_client(
            tenant_id,
            agent_identity_app_id,
            get_t1_assertion,
        )

        t2_raw: dict[str, Any] = await asyncio.to_thread(
            lambda: t2_confidential_client.acquire_token_for_client([TOKEN_EXCHANGE_SCOPE])
        )

        t2 = self._get_access_token_or_raise(t2_raw, "Agent token exchange step 2 failed")

        t3_raw: dict[str, Any] = await asyncio.to_thread(
            lambda: t2_confidential_client.acquire_token_by_user_federated_identity_credential(
                [scope],
                assertion=t2,
                user_object_id=agent_user_id,
                username=agent_user_upn,
                data={"requested_token_use": "on_behalf_of"},
            )
        )
        return self._handle_token_response(t3_raw, caller_name or "get_agent_user_token")

    def _get_access_token_or_raise(self, token_res: dict[str, Any], error_prefix: str) -> str:
        if token_res.get("access_token", None):
            return token_res["access_token"]

        error_description = token_res.get("error_description") or token_res.get("error") or "Could not acquire token"
        logger.error(f"{error_prefix}: {error_description}")
        raise ValueError(f"{error_prefix}: {error_description}")

    async def _get_token(
        self, scope: str, tenant_id: str, *, caller_name: str | None = None
    ) -> Optional[TokenProtocol]:
        credentials = self._credentials
        if self._credentials is None:
            if caller_name:
                logger.debug(f"No credentials provided for {caller_name}")
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

        confidential_client = self._get_federated_identity_client(credentials, tenant_id)

        token_res: dict[str, Any] = await asyncio.to_thread(
            lambda: confidential_client.acquire_token_for_client([scope])
        )

        return self._handle_token_response(token_res, error_prefix="FIC Step 2 failed")

    async def _acquire_managed_identity_token(self, credentials: FederatedIdentityCredentials) -> str:
        """Acquire managed identity token for federated identity credentials."""
        return await asyncio.to_thread(lambda: self._acquire_managed_identity_token_sync(credentials))

    def _acquire_managed_identity_token_sync(self, credentials: FederatedIdentityCredentials) -> str:
        """Acquire managed identity token for federated identity credentials."""
        # Use shared method to get or create the managed identity client
        mi_client = self._get_managed_identity_client(credentials)

        mi_token_res: dict[str, Any] = mi_client.acquire_token_for_client(resource="api://AzureADTokenExchange")

        if not mi_token_res.get("access_token"):
            logger.error("FIC Step 1 failed: Could not acquire MI token")
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
        agentic_identity: AgenticIdentity | None = None,
    ) -> TokenProtocol:
        """Get token using custom token provider function."""
        token = self._call_token_provider(credentials, scope, tenant_id, agentic_identity)

        if isawaitable(token):
            access_token = await token
        else:
            access_token = token

        return JsonWebToken(access_token)

    def _call_token_provider(
        self,
        credentials: TokenCredentials,
        scope: str,
        tenant_id: str,
        agentic_identity: AgenticIdentity | None = None,
    ) -> str | Awaitable[str]:
        token_provider = cast(Any, credentials.token)
        try:
            parameters = list(signature(token_provider).parameters.values())
        except (TypeError, ValueError):
            return cast(str | Awaitable[str], token_provider(scope, tenant_id, agentic_identity))

        accepts_agentic_identity = (
            any(parameter.kind == Parameter.VAR_POSITIONAL for parameter in parameters) or len(parameters) >= 3
        )
        if accepts_agentic_identity:
            return cast(str | Awaitable[str], token_provider(scope, tenant_id, agentic_identity))

        return cast(str | Awaitable[str], token_provider(scope, tenant_id))

    def _handle_token_response(self, token_res: dict[str, Any], error_prefix: str = "") -> TokenProtocol:
        """Handle token response from MSAL client."""
        if token_res.get("access_token", None):
            access_token = token_res["access_token"]
            return JsonWebToken(access_token)
        else:
            error_msg = f"{error_prefix}: " if error_prefix else ""
            logger.error(f"{error_msg}Could not acquire access token")
            logger.debug(f"TokenRes: {token_res}")

            error = token_res.get("error", "Error retrieving token")
            if not isinstance(error, BaseException):
                error = ValueError(error)

            error_description = token_res.get("error_description", "Error retrieving token from MSAL")
            logger.error(error_description)
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
            authority=f"{self._cloud.login_endpoint}/{tenant_id}",
        )
        self._confidential_clients_by_tenant[tenant_id] = client
        return client

    def _get_federated_identity_client(
        self, credentials: FederatedIdentityCredentials, tenant_id: str
    ) -> ConfidentialClientApplication:
        """Get or create ConfidentialClientApplication for FederatedIdentityCredentials."""
        cached_client = self._federated_identity_clients_by_tenant.get(tenant_id)
        if cached_client:
            return cached_client

        client: ConfidentialClientApplication = ConfidentialClientApplication(
            credentials.client_id,
            client_credential={"client_assertion": lambda: self._acquire_managed_identity_token_sync(credentials)},
            authority=f"{self._cloud.login_endpoint}/{tenant_id}",
        )
        self._federated_identity_clients_by_tenant[tenant_id] = client
        return client

    def _get_agent_identity_client(
        self,
        tenant_id: str,
        agent_identity_app_id: str,
        client_assertion: Callable[[dict[str, Any]], str],
    ) -> ConfidentialClientApplication:
        cached_client = self._agent_identity_clients_by_tenant_and_app_id.get((tenant_id, agent_identity_app_id))
        if cached_client:
            return cached_client

        client: ConfidentialClientApplication = ConfidentialClientApplication(
            agent_identity_app_id,
            client_credential={"client_assertion": client_assertion},
            authority=f"{self._cloud.login_endpoint}/{tenant_id}",
        )
        self._agent_identity_clients_by_tenant_and_app_id[(tenant_id, agent_identity_app_id)] = client
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
