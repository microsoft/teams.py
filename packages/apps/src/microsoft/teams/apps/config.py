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

    default_port: Optional[int] = None
    """Default port for HTTP server (overridden by PORT env var if not provided)"""

    def __post_init__(self):
        """Initialize default values from environment variables."""
        if self.default_port is None:
            self.default_port = _get_default_port()


@dataclass
class EndpointConfig:
    """API endpoint URLs and paths."""

    bot_api_base_url: Optional[str] = None
    """Base URL for Bot Framework API (uses BOT_API_BASE_URL env var or default)"""

    activity_path: Optional[str] = None
    """HTTP endpoint path for receiving activities (uses ACTIVITY_PATH env var or default)"""

    health_check_path: Optional[str] = None
    """HTTP endpoint for health checks (uses HEALTH_CHECK_PATH env var or default)"""

    def __post_init__(self):
        """Initialize default values from environment variables."""
        if self.bot_api_base_url is None:
            self.bot_api_base_url = os.getenv("BOT_API_BASE_URL", "https://smba.trafficmanager.net/teams")
        if self.activity_path is None:
            self.activity_path = os.getenv("ACTIVITY_PATH", "/api/messages")
        if self.health_check_path is None:
            self.health_check_path = os.getenv("HEALTH_CHECK_PATH", "/")


@dataclass
class AuthConfig:
    """Authentication and security configuration."""

    jwt_leeway_seconds: Optional[int] = None
    """Clock skew tolerance for JWT validation (seconds, uses JWT_LEEWAY_SECONDS env var or default)"""

    bot_framework_issuer: Optional[str] = None
    """Valid issuer for Bot Framework service tokens (uses BOT_FRAMEWORK_ISSUER env var or default)"""

    bot_framework_jwks_uri: Optional[str] = None
    """JWKS endpoint for Bot Framework token validation (uses BOT_FRAMEWORK_JWKS_URI env var or default)"""

    entra_id_issuer_template: Optional[str] = None
    """Template for Entra ID issuer URL (uses ENTRA_ID_ISSUER_TEMPLATE env var or default)"""

    entra_id_jwks_uri_template: Optional[str] = None
    """Template for Entra ID JWKS endpoint (uses ENTRA_ID_JWKS_URI_TEMPLATE env var or default)"""

    default_graph_tenant_id: Optional[str] = None
    """Default tenant ID for Graph API tokens (uses DEFAULT_GRAPH_TENANT_ID env var or default)"""

    def __post_init__(self):
        """Initialize default values from environment variables."""
        if self.jwt_leeway_seconds is None:
            self.jwt_leeway_seconds = int(os.getenv("JWT_LEEWAY_SECONDS", "300"))
        if self.bot_framework_issuer is None:
            self.bot_framework_issuer = os.getenv("BOT_FRAMEWORK_ISSUER", "https://api.botframework.com")
        if self.bot_framework_jwks_uri is None:
            self.bot_framework_jwks_uri = os.getenv(
                "BOT_FRAMEWORK_JWKS_URI", "https://login.botframework.com/v1/.well-known/keys"
            )
        if self.entra_id_issuer_template is None:
            self.entra_id_issuer_template = os.getenv(
                "ENTRA_ID_ISSUER_TEMPLATE", "https://login.microsoftonline.com/{tenant_id}/v2.0"
            )
        if self.entra_id_jwks_uri_template is None:
            self.entra_id_jwks_uri_template = os.getenv(
                "ENTRA_ID_JWKS_URI_TEMPLATE",
                "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys",
            )
        if self.default_graph_tenant_id is None:
            self.default_graph_tenant_id = os.getenv("DEFAULT_GRAPH_TENANT_ID", "botframework.com")


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
    """

    network: NetworkConfig = field(default_factory=NetworkConfig)
    """Network and HTTP server settings"""

    endpoints: EndpointConfig = field(default_factory=EndpointConfig)
    """API endpoint URLs and paths"""

    auth: AuthConfig = field(default_factory=AuthConfig)
    """Authentication and security settings"""


# Create a default singleton instance
DEFAULT_APP_CONFIG = AppConfig()
