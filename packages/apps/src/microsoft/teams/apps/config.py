"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class NetworkConfig:
    """Network and HTTP server configuration."""

    default_port: int = 3978
    """Default port for HTTP server (overridden by PORT env var)"""

    user_agent: Optional[str] = None
    """Custom User-Agent header (defaults to teams.py[app]/{version} if None)"""


@dataclass
class EndpointConfig:
    """API endpoint URLs and paths."""

    bot_api_base_url: str = "https://smba.trafficmanager.net/teams"
    """Base URL for Bot Framework API"""

    activity_path: str = "/api/messages"
    """HTTP endpoint path for receiving activities"""

    health_check_path: str = "/"
    """HTTP endpoint for health checks"""


@dataclass
class AuthConfig:
    """Authentication and security configuration."""

    jwt_leeway_seconds: int = 300
    """Clock skew tolerance for JWT validation (seconds)"""

    bot_framework_issuer: str = "https://api.botframework.com"
    """Valid issuer for Bot Framework service tokens"""

    bot_framework_jwks_uri: str = "https://login.botframework.com/v1/.well-known/keys"
    """JWKS endpoint for Bot Framework token validation"""

    entra_id_issuer_template: str = "https://login.microsoftonline.com/{tenant_id}/v2.0"
    """Template for Entra ID issuer URL (use {tenant_id} placeholder)"""

    entra_id_jwks_uri_template: str = (
        "https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    )
    """Template for Entra ID JWKS endpoint (use {tenant_id} placeholder)"""

    default_graph_tenant_id: str = "botframework.com"
    """Default tenant ID for Graph API tokens"""


@dataclass
class LoggerConfig:
    """Logger name configuration."""

    app_logger_name: str = "@teams/app"
    """Main application logger name"""

    http_plugin_logger_name: str = "@teams/http-plugin"
    """HTTP plugin logger name"""

    token_validator_logger_name: str = "@teams/token-validator"
    """Token validator logger name"""

    http_stream_logger_name: str = "@teams/http-stream"
    """HTTP stream logger name"""

    retry_logger_name: str = "@teams/retry"
    """Retry utility logger name"""


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
        ...         default_port=5000,
        ...         user_agent="MyCustomBot/1.0"
        ...     )
        ... )

    Attributes:
        network: Network and HTTP server settings
        endpoints: API endpoint URLs and paths
        auth: Authentication and security settings
        logger: Logger name settings
    """

    network: NetworkConfig = field(default_factory=NetworkConfig)
    """Network and HTTP server settings"""

    endpoints: EndpointConfig = field(default_factory=EndpointConfig)
    """API endpoint URLs and paths"""

    auth: AuthConfig = field(default_factory=AuthConfig)
    """Authentication and security settings"""

    logger: LoggerConfig = field(default_factory=LoggerConfig)
    """Logger name settings"""


# Create a default singleton instance
DEFAULT_APP_CONFIG = AppConfig()
