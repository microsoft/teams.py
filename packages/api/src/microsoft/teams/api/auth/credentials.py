"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Optional, Union

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


# Union type for credentials
Credentials = Union[ClientCredentials, TokenCredentials]
