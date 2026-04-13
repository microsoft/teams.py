"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .caller import CallerIds, CallerType
from .cloud_environment import (
    CloudEnvironment,
    with_overrides,
)
from .cloud_environment import from_name as config_from_cloud_name
from .credentials import (
    ClientCredentials,
    Credentials,
    FederatedIdentityCredentials,
    ManagedIdentityCredentials,
    TokenCredentials,
)
from .json_web_token import JsonWebToken, JsonWebTokenPayload
from .token import TokenProtocol

__all__ = [
    "CallerIds",
    "CallerType",
    "CloudEnvironment",
    "ClientCredentials",
    "config_from_cloud_name",
    "Credentials",
    "FederatedIdentityCredentials",
    "ManagedIdentityCredentials",
    "TokenCredentials",
    "TokenProtocol",
    "JsonWebToken",
    "JsonWebTokenPayload",
    "with_overrides",
]
