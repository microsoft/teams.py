"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from logging import Logger
from typing import Any, Awaitable, Callable, List, Optional, TypedDict, Union, cast

from microsoft.teams.api import DEFAULT_API_CLIENT_SETTINGS, ApiClientSettings
from microsoft.teams.common import Storage
from typing_extensions import Unpack

from .plugins import PluginBase


@dataclass
class OAuthSettings:
    """OAuth configuration settings.

    Attributes:
        default_connection_name: The OAuth connection name to use for authentication.
        client_settings: Client settings for authentication. Important for configuring regional bots.
    """

    default_connection_name: str = "graph"
    client_settings: ApiClientSettings = field(default_factory=lambda: DEFAULT_API_CLIENT_SETTINGS)


class AppOptions(TypedDict, total=False):
    """Configuration options for the Teams App."""

    client_id: Optional[str]
    """The client ID of the app registration."""
    client_secret: Optional[str]
    """The client secret. If provided with client_id, uses ClientCredentials auth."""
    tenant_id: Optional[str]
    """The tenant ID. Required for single-tenant apps."""
    # Custom token provider function
    token: Optional[Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]]]
    """Custom token provider function. If provided with client_id (no client_secret), uses TokenCredentials."""

    # Managed identity configuration (used when client_id provided without client_secret or token)
    managed_identity_client_id: Optional[str]
    """
    The managed identity client ID for user-assigned managed identity.
    Set to "system" for system-assigned managed identity (triggers Federated Identity Credentials).
    If set to a different client ID than client_id, triggers Federated Identity Credentials with user-assigned MI.
    If not set or equals client_id, uses direct managed identity (no federation).
    """

    # Infrastructure
    logger: Optional[Logger]
    storage: Optional[Storage[str, Any]]
    plugins: Optional[List[PluginBase]]
    skip_auth: Optional[bool]

    # OAuth
    default_connection_name: Optional[str]
    """DEPRECATED: Use oauth instead. The OAuth connection name to use for authentication. Defaults to 'graph'."""
    oauth: Optional[OAuthSettings]
    """OAuth settings including connection name and client settings for regional bots."""


@dataclass
class InternalAppOptions:
    """Internal dataclass for AppOptions with defaults and non-nullable fields."""

    # Fields with defaults
    skip_auth: bool = False
    default_connection_name: str = "graph"
    """DEPRECATED: Use oauth.default_connection_name instead."""
    oauth: OAuthSettings = field(default_factory=OAuthSettings)
    plugins: List[PluginBase] = field(default_factory=lambda: [])

    # Optional fields
    client_id: Optional[str] = None
    """The client ID of the app registration."""
    client_secret: Optional[str] = None
    """The client secret. If provided with client_id, uses ClientCredentials auth."""
    tenant_id: Optional[str] = None
    """The tenant ID. Required for single-tenant apps."""
    token: Optional[Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]]] = None
    """Custom token provider function. If provided with client_id (no client_secret), uses TokenCredentials."""
    managed_identity_client_id: Optional[str] = None
    """
    The managed identity client ID for user-assigned managed identity.
    Set to "system" for system-assigned managed identity (triggers Federated Identity Credentials).
    If set to a different client ID than client_id, triggers Federated Identity Credentials with user-assigned MI.
    If not set or equals client_id, uses direct managed identity (no federation).
    """
    logger: Optional[Logger] = None
    storage: Optional[Storage[str, Any]] = None

    @classmethod
    def from_typeddict(cls, options: AppOptions) -> "InternalAppOptions":
        """
        Create InternalAppOptions from AppOptions TypedDict with defaults applied.

        Args:
            options: AppOptions TypedDict (potentially with None values)

        Returns:
            InternalAppOptions with proper defaults and non-nullable required fields
        """
        kwargs: dict[str, Any] = {}

        # Handle OAuth settings
        if "oauth" in options and options["oauth"] is not None:
            kwargs["oauth"] = options["oauth"]
        elif "default_connection_name" in options and options["default_connection_name"] is not None:
            # Support legacy default_connection_name field
            kwargs["oauth"] = OAuthSettings(default_connection_name=options["default_connection_name"])
            kwargs["default_connection_name"] = options["default_connection_name"]

        # Copy other fields
        for key, value in options.items():
            if key not in ("oauth", "default_connection_name") and value is not None:
                kwargs[key] = value

        return cls(**kwargs)


def merge_app_options_with_defaults(**options: Unpack[AppOptions]) -> AppOptions:
    """
    Create AppOptions with default values merged with provided options.

    Args:
        **options: Configuration options to override defaults

    Returns:
        AppOptions with defaults applied
    """
    defaults: AppOptions = {
        "skip_auth": False,
        "default_connection_name": "graph",
        "plugins": [],
    }

    return cast(AppOptions, {**defaults, **options})
