"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, replace
from typing import Optional


@dataclass(frozen=True)
class CloudEnvironment:
    """
    Bundles all cloud-specific service endpoints for a given Azure environment.
    Use predefined instances (PUBLIC, US_GOV, US_GOV_DOD, CHINA)
    or construct a custom one via with_overrides().
    """

    login_endpoint: str
    """The Azure AD login endpoint (e.g. "https://login.microsoftonline.com")."""
    login_tenant: str
    """The default multi-tenant login tenant (e.g. "botframework.com")."""
    bot_scope: str
    """The Bot Framework OAuth scope (e.g. "https://api.botframework.com/.default")."""
    agentic_bot_scope: str
    """The Teams Bot API scope for Agent ID user-token calls."""
    token_service_url: str
    """The Bot Framework token service base URL (e.g. "https://token.botframework.com")."""
    openid_metadata_url: str
    """The OpenID metadata URL for token validation."""
    token_issuer: str
    """The token issuer for Bot Framework tokens (e.g. "https://api.botframework.com")."""
    graph_scope: str
    """The Microsoft Graph token scope (e.g. "https://graph.microsoft.com/.default")."""


PUBLIC = CloudEnvironment(
    login_endpoint="https://login.microsoftonline.com",
    login_tenant="botframework.com",
    bot_scope="https://api.botframework.com/.default",
    agentic_bot_scope="https://botapi.skype.com/.default",
    token_service_url="https://token.botframework.com",
    openid_metadata_url="https://login.botframework.com/v1/.well-known/openidconfiguration",
    token_issuer="https://api.botframework.com",
    graph_scope="https://graph.microsoft.com/.default",
)
"""Microsoft public (commercial) cloud."""

US_GOV = CloudEnvironment(
    login_endpoint="https://login.microsoftonline.us",
    login_tenant="MicrosoftServices.onmicrosoft.us",
    bot_scope="https://api.botframework.us/.default",
    agentic_bot_scope="https://botapi.skype.com/.default",
    token_service_url="https://tokengcch.botframework.azure.us",
    openid_metadata_url="https://login.botframework.azure.us/v1/.well-known/openidconfiguration",
    token_issuer="https://api.botframework.us",
    graph_scope="https://graph.microsoft.us/.default",
)
"""US Government Community Cloud High (GCCH)."""

US_GOV_DOD = CloudEnvironment(
    login_endpoint="https://login.microsoftonline.us",
    login_tenant="MicrosoftServices.onmicrosoft.us",
    bot_scope="https://api.botframework.us/.default",
    agentic_bot_scope="https://botapi.skype.com/.default",
    token_service_url="https://apiDoD.botframework.azure.us",
    openid_metadata_url="https://login.botframework.azure.us/v1/.well-known/openidconfiguration",
    token_issuer="https://api.botframework.us",
    graph_scope="https://dod-graph.microsoft.us/.default",
)
"""US Government Department of Defense (DoD)."""

CHINA = CloudEnvironment(
    login_endpoint="https://login.partner.microsoftonline.cn",
    login_tenant="microsoftservices.partner.onmschina.cn",
    bot_scope="https://api.botframework.azure.cn/.default",
    agentic_bot_scope="https://botapi.skype.com/.default",
    token_service_url="https://token.botframework.azure.cn",
    openid_metadata_url="https://login.botframework.azure.cn/v1/.well-known/openidconfiguration",
    token_issuer="https://api.botframework.azure.cn",
    graph_scope="https://microsoftgraph.chinacloudapi.cn/.default",
)
"""China cloud (21Vianet)."""

_CLOUD_ENVIRONMENTS: dict[str, CloudEnvironment] = {
    "public": PUBLIC,
    "usgov": US_GOV,
    "usgovdod": US_GOV_DOD,
    "china": CHINA,
}


def from_name(name: str) -> CloudEnvironment:
    """
    Resolve a cloud environment name (case-insensitive) to its corresponding instance.
    Valid names: "Public", "USGov", "USGovDoD", "China".
    """
    env = _CLOUD_ENVIRONMENTS.get(name.lower())
    if env is None:
        raise ValueError(f"Unknown cloud environment: '{name}'. Valid values are: Public, USGov, USGovDoD, China.")
    return env


def with_overrides(base: CloudEnvironment, **overrides: Optional[str]) -> CloudEnvironment:
    """
    Create a new CloudEnvironment by applying non-None overrides on top of a base.
    Returns the same instance if all overrides are None (no allocation).
    """
    filtered = {k: v for k, v in overrides.items() if v is not None}
    if not filtered:
        return base
    return replace(base, **filtered)
