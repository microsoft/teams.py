"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Optional, Union, cast

from microsoft_teams.common import Client as HttpClient
from microsoft_teams.common import ClientOptions, Interceptor
from typing_extensions import deprecated

from ..auth.cloud_environment import PUBLIC, CloudEnvironment
from ..models import AgenticIdentity
from ._auth_provider_interceptor import AuthProvider, AuthProviderInterceptor
from .api_client_settings import ApiClientSettings, merge_api_client_settings
from .base_client import BaseClient
from .bot import BotClient  # pyright: ignore[reportDeprecated]
from .conversation import ConversationClient
from .meeting import MeetingClient
from .reaction import ReactionClient
from .team import TeamClient
from .user import UserClient


class ApiClient(BaseClient):
    """Unified client for Microsoft Teams API operations."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[HttpClient, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        cloud: Optional[CloudEnvironment] = None,
        *,
        auth_provider: Optional[AuthProvider] = None,
        agentic_identity: Optional[AgenticIdentity] = None,
    ) -> None:
        """Initialize the unified Teams API client.

        Args:
            service_url: The Teams service URL for API calls.
            options: Either an HTTP client instance or client options. If None, a default client is created.
            api_client_settings: Optional API client settings.
            cloud: Optional cloud environment for sovereign cloud support.
        """
        self._cloud = cloud or PUBLIC
        merged_settings = merge_api_client_settings(api_client_settings, self._cloud)
        super().__init__(options, merged_settings)
        self.service_url = service_url.rstrip("/")
        self._auth_provider = auth_provider
        self._default_agentic_identity = agentic_identity
        self._apply_auth_provider_interceptor()

        # Initialize all client types
        self._bots = BotClient(  # pyright: ignore[reportDeprecated]
            self._http, self._api_client_settings, cloud=self._cloud
        )
        self.users = UserClient(self._http, self._api_client_settings, cloud=self._cloud)
        self.conversations = ConversationClient(self.service_url, self._http, self._api_client_settings)
        self.teams = TeamClient(self.service_url, self._http, self._api_client_settings)
        self.meetings = MeetingClient(self.service_url, self._http, self._api_client_settings)
        self._reactions: Optional[ReactionClient] = None

    @property
    @deprecated("The bot client is no longer used and will be removed in a future release.")
    def bots(self):
        """Get the bot client."""
        return self._bots

    @property
    @deprecated(
        "Use `conversations.add_reaction(...)` and `conversations.delete_reaction(...)` instead. "
        "This will be removed in a future release."
    )
    def reactions(self) -> ReactionClient:
        """Get the reactions client (preview). Lazily instantiated to avoid warnings for non-users."""
        if self._reactions is None:
            self._reactions = ReactionClient(self.service_url, self._http, self._api_client_settings)
        return self._reactions

    def _apply_auth_provider_interceptor(self) -> None:
        if self._auth_provider is None:
            return

        if any(isinstance(interceptor, AuthProviderInterceptor) for interceptor in self._http.interceptors):
            return

        self._http.use_interceptor(
            cast(
                Interceptor,
                AuthProviderInterceptor(
                    self._auth_provider,
                    default_agentic_identity=self._default_agentic_identity,
                ),
            )
        )

    @property
    def http(self) -> HttpClient:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: HttpClient) -> None:
        """Set the HTTP client instance and propagate to all sub-clients."""
        self._http = value
        self._apply_auth_provider_interceptor()
        self._bots.http = self._http
        self.conversations.http = self._http
        self.users.http = self._http
        self.teams.http = self._http
        self.meetings.http = self._http
        if self._reactions is not None:
            self._reactions.http = self._http
