"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Optional, Protocol, Union

from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment
from microsoft_teams.common.http import Client, ClientOptions
from microsoft_teams.common.http.client_token import StringLike

from ..models.agentic_identity import AgenticIdentity
from .api_client_settings import ApiClientSettings, merge_api_client_settings


class AuthProvider(Protocol):
    def token(
        self, scope: str, tenant_id: str | None = None, agentic_identity: AgenticIdentity | None = None
    ) -> str | StringLike | None | Awaitable[str | StringLike | None]: ...


class BaseClient:
    """Base client"""

    def __init__(
        self,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        *,
        auth_provider: Optional[AuthProvider] = None,
        cloud: Optional[CloudEnvironment] = None,
    ) -> None:
        """Initialize the BaseClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        if options is None:
            self._http = Client(ClientOptions())
        elif isinstance(options, Client):
            self._http = options
        else:
            self._http = Client(options)

        self._api_client_settings = merge_api_client_settings(api_client_settings)
        self._auth_provider = auth_provider
        self._cloud = cloud or PUBLIC

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance."""
        self._http = value

    def _get_agentic_token(self, identity: AgenticIdentity | None):
        if identity is None:
            return None
        if self._auth_provider is None:
            raise ValueError("agentic_identity requires a Teams auth provider")
        auth_provider = self._auth_provider

        return lambda: auth_provider.token(self._cloud.agentic_bot_scope, identity.tenant_id, identity)
