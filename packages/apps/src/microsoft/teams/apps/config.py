"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


def _get_default_port() -> int:
    """Get default port from PORT env var or use 3978."""
    return int(os.getenv("PORT", "3978"))


@dataclass
class NetworkConfig:
    """Network and HTTP server configuration."""

    default_port: int = field(default_factory=_get_default_port)
    """Default port for HTTP server (overridden by PORT env var if not provided)"""


@dataclass
class EndpointConfig:
    """API endpoint URLs and paths."""

    api_base_url: str = field(
        default_factory=lambda: os.getenv("API_BASE_URL", "https://smba.trafficmanager.net/teams")
    )
    """Base URL for Bot Framework API (uses API_BASE_URL env var or default)"""

    activity_path: str = field(default_factory=lambda: os.getenv("ACTIVITY_PATH", "/api/messages"))
    """HTTP endpoint path for receiving activities (uses ACTIVITY_PATH env var or default)"""


@dataclass
class AuthConfig:
    """Authentication and security configuration."""

    jwt_leeway_seconds: int = field(default_factory=lambda: int(os.getenv("JWT_LEEWAY_SECONDS", "300")))
    """Clock skew tolerance for JWT validation (seconds, uses JWT_LEEWAY_SECONDS env var or default)"""

    bot_framework_issuer: str = field(
        default_factory=lambda: os.getenv("BOT_FRAMEWORK_ISSUER", "https://api.botframework.com")
    )
    """Valid issuer for Bot Framework service tokens (uses BOT_FRAMEWORK_ISSUER env var or default)"""

    bot_framework_jwks_uri: str = field(
        default_factory=lambda: os.getenv(
            "BOT_FRAMEWORK_JWKS_URI", "https://login.botframework.com/v1/.well-known/keys"
        )
    )
    """JWKS endpoint for Bot Framework token validation (uses BOT_FRAMEWORK_JWKS_URI env var or default)"""

    entra_id_issuer_template: str = field(
        default_factory=lambda: os.getenv(
            "ENTRA_ID_ISSUER_TEMPLATE", "https://login.microsoftonline.com/{tenant_id}/v2.0"
        )
    )
    """Template for Entra ID issuer URL (uses ENTRA_ID_ISSUER_TEMPLATE env var or default)"""

    entra_id_jwks_uri_template: str = field(
        default_factory=lambda: os.getenv(
            "ENTRA_ID_JWKS_URI_TEMPLATE",
            "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
        )
    )
    """Template for Entra ID JWKS URI (uses ENTRA_ID_JWKS_URI_TEMPLATE env var or default)"""


@dataclass
class SignInConfig:
    """Sign-in UI configuration."""

    oauth_card_text: str = field(default_factory=lambda: os.getenv("OAUTH_CARD_TEXT", "Please Sign In..."))
    """Default text for OAuth card (uses OAUTH_CARD_TEXT env var or default)"""

    sign_in_button_text: str = field(default_factory=lambda: os.getenv("SIGN_IN_BUTTON_TEXT", "Sign In"))
    """Default text for sign-in button (uses SIGN_IN_BUTTON_TEXT env var or default)"""


@dataclass
class CredentialsConfig:
    """Application credentials configuration."""

    client_id: Optional[str] = field(default_factory=lambda: os.getenv("CLIENT_ID"))
    """Application client ID (uses CLIENT_ID env var if not provided)"""

    client_secret: Optional[str] = field(default_factory=lambda: os.getenv("CLIENT_SECRET"))
    """Application client secret (uses CLIENT_SECRET env var if not provided)"""

    tenant_id: Optional[str] = field(default_factory=lambda: os.getenv("TENANT_ID"))
    """Application tenant ID (uses TENANT_ID env var if not provided)"""


@dataclass
class AppConfig:
    """
    Centralized configuration for Teams application.

    All hardcoded constants are now configurable through this object.
    Users can customize behavior by passing a custom AppConfig to their application.

    Example:
        >>> from microsoft.teams.apps import AppConfig, NetworkConfig
        >>> # Customize network settings
        >>> config = AppConfig(
        ...     network=NetworkConfig(
        ...         default_port=5000
        ...     )
        ... )

    Attributes:
        network: Network and HTTP server settings
        endpoints: API endpoint URLs and paths
        auth: Authentication and security settings
        signin: Sign-in UI settings
        credentials: Application credentials (client_id, client_secret, tenant_id)
    """

    network: NetworkConfig = field(default_factory=NetworkConfig)
    """Network and HTTP server settings"""

    endpoints: EndpointConfig = field(default_factory=EndpointConfig)
    """API endpoint URLs and paths"""

    auth: AuthConfig = field(default_factory=AuthConfig)
    """Authentication and security settings"""

    signin: SignInConfig = field(default_factory=SignInConfig)
    """Sign-in UI settings"""

    credentials: Optional[CredentialsConfig] = None
    """Application credentials (optional, will be populated from AppOptions if not provided)"""


# Create a default singleton instance
DEFAULT_APP_CONFIG = AppConfig()
