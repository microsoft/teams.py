"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Literal, Optional, Protocol, TypeAlias, Union, runtime_checkable

from ..models import AgenticIdentity, CustomBaseModel
from .token import TokenProtocol

TokenScope: TypeAlias = Union[str, list[str]]
TokenValue: TypeAlias = Union[str, TokenProtocol, None]
TokenResult: TypeAlias = Union[TokenValue, Awaitable[TokenValue]]
BasicTokenProvider: TypeAlias = Callable[[TokenScope, Optional[str]], TokenResult]


@runtime_checkable
class TokenProviderProtocol(Protocol):
    """Named token capabilities for apps that need more than app-only tokens."""

    def get_app_token(
        self,
        scope: str,
        tenant_id: Optional[str],
    ) -> TokenResult: ...


@runtime_checkable
class AgenticIdentityTokenProviderProtocol(TokenProviderProtocol, Protocol):
    """Optional named capability for acquiring agentic identity-scoped tokens."""

    def get_agentic_identity_token(
        self,
        scope: str,
        agentic_identity: AgenticIdentity,
    ) -> TokenResult: ...


@runtime_checkable
class AgenticUserTokenProviderProtocol(TokenProviderProtocol, Protocol):
    """Optional named capability for acquiring agentic user-scoped tokens."""

    def get_agentic_user_token(
        self,
        scope: str,
        agentic_app_id: str,
        agentic_user_id: str,
        tenant_id: Optional[str],
    ) -> TokenResult: ...


@runtime_checkable
class AgenticAppTokenProviderProtocol(TokenProviderProtocol, Protocol):
    """Optional named capability for acquiring agentic app-scoped tokens."""

    def get_agentic_app_token(
        self,
        scope: str,
        agentic_app_id: str,
        tenant_id: Optional[str],
    ) -> TokenResult: ...


TokenProvider: TypeAlias = Union[BasicTokenProvider, TokenProviderProtocol]


class ClientCredentials(CustomBaseModel):
    """Credentials for authentication of an app via clientId and clientSecret."""

    client_id: str
    """
    The client ID.
    """
    client_secret: str
    """
    The client secret.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID. This should only be passed in for single tenant apps.
    """


class TokenCredentials(CustomBaseModel):
    """Credentials for authentication of an app via any external auth method."""

    client_id: str
    """
    The client ID.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID.
    """
    token: TokenProvider
    """
    A callable for app-only tokens, or a named token provider for app-only and agentic grants.
    """


class ManagedIdentityCredentials(CustomBaseModel):
    """Credentials for authentication using Azure User-Assigned Managed Identity."""

    client_id: str
    """
    The client ID of the user-assigned managed identity.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID.
    """


class FederatedIdentityCredentials(CustomBaseModel):
    """Credentials for authentication using Federated Identity Credentials with Managed Identity."""

    client_id: str
    """
    The client ID of the app registration.
    """
    managed_identity_type: Literal["system", "user"]
    """
    The type of managed identity: 'system' for system-assigned or 'user' for user-assigned.
    """
    managed_identity_client_id: Optional[str] = None
    """
    The client ID of the user-assigned managed identity.
    Required when managed_identity_type is 'user'.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID.
    """


# Union type for credentials
Credentials = Union[ClientCredentials, TokenCredentials, ManagedIdentityCredentials, FederatedIdentityCredentials]
