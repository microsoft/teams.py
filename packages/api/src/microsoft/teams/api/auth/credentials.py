"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Literal, Optional, Union

from ..models import CustomBaseModel


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
    # (scope: string | string[], tenantId?: string) => string | Promise<string>
    token: Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]]
    """
    The token function.
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
