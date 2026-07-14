"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import os
import warnings
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List, Optional, TypedDict, Union, cast

from microsoft_teams.api import ApiClientSettings
from microsoft_teams.api.auth.cloud_environment import CloudEnvironment
from microsoft_teams.common import Client, ClientOptions, Storage
from typing_extensions import Unpack

from .http.adapter import HttpServerAdapter
from .plugins import PluginBase

DANGEROUSLY_ALLOW_UNAUTHENTICATED_REQUESTS_ENV_VAR = "DANGEROUSLY_ALLOW_UNAUTHENTICATED_REQUESTS"
_TRUE_ENV_VALUES = {"1", "true", "yes", "on"}
_FALSE_ENV_VALUES = {"0", "false", "no", "off"}


def _parse_bool_env_var(name: str) -> Optional[bool]:
    value = os.getenv(name)
    if value is None:
        return None

    normalized_value = value.strip().lower()
    if not normalized_value:
        return None
    if normalized_value in _TRUE_ENV_VALUES:
        return True
    if normalized_value in _FALSE_ENV_VALUES:
        return False

    raise ValueError(f"{name} must be a boolean value: true/false, 1/0, yes/no, or on/off.")


def _warn_skip_auth_deprecated() -> None:
    warnings.warn(
        "skip_auth is deprecated; use dangerously_allow_unauthenticated_requests instead.",
        DeprecationWarning,
        stacklevel=3,
    )


class AppOptions(TypedDict, total=False):
    """Configuration options for the Teams App."""

    client_id: Optional[str]
    """The client ID of the app registration."""
    client_secret: Optional[str]
    """The client secret. If provided with client_id, uses ClientCredentials auth."""
    tenant_id: Optional[str]
    """The tenant ID. Required for single-tenant apps."""
    application_id_uri: Optional[str]
    """Application ID URI from the Azure portal. Used for user authentication.
    Matches webApplicationInfo.resource in the app manifest."""
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

    # HTTP client
    client: Optional[Union[Client, ClientOptions]]
    """HTTP client or client options used to make API requests.
    Accepts a Client instance or ClientOptions. The app always injects its own User-Agent header."""

    # Infrastructure
    storage: Optional[Storage[str, Any]]
    plugins: Optional[List[PluginBase]]
    dangerously_allow_unauthenticated_requests: Optional[bool]
    """
    Whether to accept incoming requests without JWT validation.
    Defaults to the DANGEROUSLY_ALLOW_UNAUTHENTICATED_REQUESTS environment variable, or False.
    """
    skip_auth: Optional[bool]
    """Deprecated. Use dangerously_allow_unauthenticated_requests instead."""

    # HTTP adapter
    http_server_adapter: Optional[HttpServerAdapter]
    """Custom HTTP server adapter. Defaults to FastAPIAdapter if not provided."""

    messaging_endpoint: Optional[str]
    """URL path for the Teams messaging endpoint. Defaults to '/api/messages'."""

    # OAuth
    default_connection_name: Optional[str]
    """The OAuth connection name to use for authentication. Defaults to 'graph'."""

    # API Client Settings
    api_client_settings: Optional[ApiClientSettings]
    """API client settings used for overriding."""

    # Service URL
    service_url: Optional[str]
    """
    Base Service URL for BotBackend.
    Uses environment variable SERVICE_URL if not provided
    and defaults to https://smba.trafficmanager.net/teams
    """

    # Cloud environment
    cloud: Optional[CloudEnvironment]
    """
    Cloud environment for sovereign cloud support.
    Accepts a CloudEnvironment instance or uses CLOUD environment variable.
    Valid env var values: "Public", "USGov", "USGovDoD", "China".
    Defaults to PUBLIC (commercial cloud).
    """


@dataclass
class InternalAppOptions:
    """Internal dataclass for AppOptions with defaults and non-nullable fields."""

    # Fields with defaults
    dangerously_allow_unauthenticated_requests: bool = False
    """Whether to accept incoming requests without JWT validation."""
    default_connection_name: str = "graph"
    """The OAuth connection name to use for authentication."""
    plugins: List[PluginBase] = field(default_factory=lambda: [])
    api_client_settings: Optional[ApiClientSettings] = None
    """API client settings used for overriding."""

    # HTTP client
    client: Optional[Union[Client, ClientOptions]] = None
    """HTTP client or client options used to make API requests."""

    # Optional fields
    client_id: Optional[str] = None
    """The client ID of the app registration."""
    client_secret: Optional[str] = None
    """The client secret. If provided with client_id, uses ClientCredentials auth."""
    tenant_id: Optional[str] = None
    """The tenant ID. Required for single-tenant apps."""
    application_id_uri: Optional[str] = None
    """Application ID URI from the Azure portal. Used for user authentication.
    Matches webApplicationInfo.resource in the app manifest."""
    token: Optional[Callable[[Union[str, list[str]], Optional[str]], Union[str, Awaitable[str]]]] = None
    """Custom token provider function. If provided with client_id (no client_secret), uses TokenCredentials."""
    managed_identity_client_id: Optional[str] = None
    """
    The managed identity client ID for user-assigned managed identity.
    Set to "system" for system-assigned managed identity (triggers Federated Identity Credentials).
    If set to a different client ID than client_id, triggers Federated Identity Credentials with user-assigned MI.
    If not set or equals client_id, uses direct managed identity (no federation).
    """
    storage: Optional[Storage[str, Any]] = None
    service_url: Optional[str] = None
    """
    Base Service URL for BotBackend.
    Uses environment variable SERVICE_URL if not provided
    and defaults to https://smba.trafficmanager.net/teams
    """
    http_server_adapter: Optional[HttpServerAdapter] = None
    """Custom HTTP server adapter. Defaults to FastAPIAdapter if not provided."""
    messaging_endpoint: str = "/api/messages"
    """URL path for the Teams messaging endpoint. Defaults to '/api/messages'."""
    cloud: Optional[CloudEnvironment] = None
    """Cloud environment for sovereign cloud support."""

    @classmethod
    def from_typeddict(cls, options: AppOptions) -> "InternalAppOptions":
        """
        Create InternalAppOptions from AppOptions TypedDict with defaults applied.

        Args:
            options: AppOptions TypedDict (potentially with None values)

        Returns:
            InternalAppOptions with proper defaults and non-nullable required fields
        """
        kwargs: dict[str, Any] = {k: v for k, v in options.items() if v is not None}
        dangerously_allow_unauthenticated_requests = kwargs.pop("dangerously_allow_unauthenticated_requests", None)
        skip_auth = kwargs.pop("skip_auth", None)

        if skip_auth is not None:
            _warn_skip_auth_deprecated()

        if dangerously_allow_unauthenticated_requests is None:
            if skip_auth is not None:
                dangerously_allow_unauthenticated_requests = skip_auth
            else:
                dangerously_allow_unauthenticated_requests = (
                    _parse_bool_env_var(DANGEROUSLY_ALLOW_UNAUTHENTICATED_REQUESTS_ENV_VAR) or False
                )
        kwargs["dangerously_allow_unauthenticated_requests"] = dangerously_allow_unauthenticated_requests
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
        "dangerously_allow_unauthenticated_requests": False,
        "skip_auth": False,
        "default_connection_name": "graph",
        "plugins": [],
    }

    return cast(AppOptions, {**defaults, **options})
