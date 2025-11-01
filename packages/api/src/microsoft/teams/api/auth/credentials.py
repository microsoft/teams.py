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


class CertificateCredentials(CustomBaseModel):
    """Credentials for authentication using X.509 certificate (PEM format)."""

    client_id: str
    """
    The client ID.
    """
    private_key: str
    """
    The private key in PEM format.
    """
    thumbprint: str
    """
    The SHA-1 thumbprint of the certificate.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID. This should only be passed in for single tenant apps.
    """


class ManagedIdentityCredentials(CustomBaseModel):
    """Credentials for authentication using Azure Managed Identity."""

    client_id: str
    """
    The client ID of the app registration.
    """
    managed_identity_type: Literal["system", "user"]
    """
    The type of managed identity: 'system' for system-assigned or 'user' for user-assigned.
    """
    tenant_id: Optional[str] = None
    """
    The tenant ID.
    """


# Union type for credentials
Credentials = Union[ClientCredentials, TokenCredentials, CertificateCredentials, ManagedIdentityCredentials]
