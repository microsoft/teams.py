"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Literal, Optional, TypeAlias, Union

from microsoft_teams.common import Client as HttpClient
from microsoft_teams.common import ClientOptions, Token
from typing_extensions import deprecated

from ..auth.cloud_environment import PUBLIC, CloudEnvironment
from ..models import AgenticIdentity
from ._auth_provider import AuthProvider
from .api_client_settings import ApiClientSettings, merge_api_client_settings
from .base_client import BaseClient
from .bot import BotClient  # pyright: ignore[reportDeprecated]
from .conversation import ConversationClient
from .meeting import MeetingClient
from .reaction import ReactionClient
from .team import TeamClient
from .user import UserClient

AgenticIdentityClear: TypeAlias = Literal["clear"]
AGENTIC_IDENTITY_CLEAR: AgenticIdentityClear = "clear"
AgenticIdentityScope: TypeAlias = AgenticIdentity | None | AgenticIdentityClear


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
        if auth_provider is not None and self._http.token is not None:
            raise ValueError("Cannot use both an auth provider and an HTTP client token.")

        self._auth_provider = auth_provider
        self._default_agentic_identity = agentic_identity
        self._apply_auth_provider_token()

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

    def clone(
        self,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentityScope = None,
    ) -> "ApiClient":
        """Create a scoped API client.

        Omitting agentic_identity, or passing None, preserves the existing scoped identity.
        Pass AGENTIC_IDENTITY_CLEAR to clear it, or an AgenticIdentity to override it.
        """
        if agentic_identity is None:
            resolved_agentic_identity = self._default_agentic_identity
        elif agentic_identity == AGENTIC_IDENTITY_CLEAR:
            resolved_agentic_identity = None
        else:
            resolved_agentic_identity = agentic_identity
        http = self._http.clone(share_http=True)
        if self._auth_provider is not None:
            http.token = None

        return ApiClient(
            service_url or self.service_url,
            http,
            self._api_client_settings,
            cloud=self._cloud,
            auth_provider=self._auth_provider,
            agentic_identity=resolved_agentic_identity,
        )

    def from_service_url(self, service_url: str) -> "ApiClient":
        """Create a scoped API client for a different Teams service URL."""
        return self.clone(service_url=service_url)

    def from_agentic_identity(self, agentic_identity: AgenticIdentity) -> "ApiClient":
        """Create a scoped API client for an agentic identity."""
        return self.clone(agentic_identity=agentic_identity)

    def for_agentic_identity(self, agentic_identity: AgenticIdentity) -> "ApiClient":
        """Alias for from_agentic_identity."""
        return self.from_agentic_identity(agentic_identity)

    def _get_scoped_http(self, agentic_identity: AgenticIdentity | None) -> HttpClient:
        if self._auth_provider is None:
            return self._http.clone(share_http=True)

        return self._http.clone(
            ClientOptions(token=self._create_auth_provider_token(agentic_identity)),
            share_http=True,
        )

    def _apply_auth_provider_token(self) -> None:
        if self._auth_provider is None:
            return

        self._http = self._get_scoped_http(self._default_agentic_identity)

    def _create_auth_provider_token(self, agentic_identity: AgenticIdentity | None) -> Token:
        auth_provider = self._auth_provider
        if auth_provider is None:
            return None

        return lambda: auth_provider.token(agentic_identity=agentic_identity)

    @property
    def http(self) -> HttpClient:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: HttpClient) -> None:
        """Set the HTTP client instance and propagate to all sub-clients."""
        self._http = value
        self._apply_auth_provider_token()
        self._bots.http = self._http
        self.conversations.http = self._http
        self.users.http = self._http
        self.teams.http = self._http
        self.meetings.http = self._http
        if self._reactions is not None:
            self._reactions.http = self._http
