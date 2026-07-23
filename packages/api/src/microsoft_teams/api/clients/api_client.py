"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import inspect
from typing import Literal, Optional, TypeAlias, Union

from microsoft_teams.common import Client as HttpClient
from microsoft_teams.common import ClientOptions, Token
from microsoft_teams.common.http.client_token import StringLike
from opentelemetry.trace import SpanKind
from typing_extensions import deprecated

from ..auth.cloud_environment import PUBLIC, CloudEnvironment
from ..diagnostics._constants import API_ATTRIBUTE_NAMES, API_AUTH_FLOWS, API_SPAN_NAMES
from ..diagnostics._helpers import get_tracer, record_exception
from ..diagnostics._outbound import ensure_outbound_telemetry_middleware
from ..models import AgenticUser
from ._auth_provider import AuthProvider
from .api_client_settings import ApiClientSettings, merge_api_client_settings
from .base_client import BaseClient
from .bot import BotClient  # pyright: ignore[reportDeprecated]
from .conversation import ConversationClient
from .meeting import MeetingClient
from .reaction import ReactionClient
from .team import TeamClient
from .user import UserClient

AgenticUserClear: TypeAlias = Literal["clear"]
AGENTIC_USER_CLEAR: AgenticUserClear = "clear"
AgenticUserScope: TypeAlias = AgenticUser | None | AgenticUserClear


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
        agentic_user: Optional[AgenticUser] = None,
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
        self._default_agentic_user = agentic_user
        self._apply_auth_provider_token()

        # Initialize all client types
        self._bots = BotClient(  # pyright: ignore[reportDeprecated]
            self._http, self._api_client_settings, cloud=self._cloud
        )
        self.users = UserClient(self._http, self._api_client_settings, cloud=self._cloud)
        self.conversations = ConversationClient(
            self.service_url,
            self._http,
            self._api_client_settings,
            scope_factory=self._scope_conversations,
        )
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
        agentic_user: AgenticUserScope = None,
    ) -> "ApiClient":
        """Create a scoped API client.

        Omitting agentic_user, or passing None, preserves the existing scoped identity.
        Pass AGENTIC_USER_CLEAR to clear it, or an AgenticUser to override it.
        """
        if agentic_user is None:
            resolved_agentic_user = self._default_agentic_user
        elif agentic_user == AGENTIC_USER_CLEAR:
            resolved_agentic_user = None
        else:
            resolved_agentic_user = agentic_user
        http = self._http.clone(share_http=True)
        if self._auth_provider is not None:
            http.token = None

        return ApiClient(
            service_url or self.service_url,
            http,
            self._api_client_settings,
            cloud=self._cloud,
            auth_provider=self._auth_provider,
            agentic_user=resolved_agentic_user,
        )

    def from_service_url(self, service_url: str) -> "ApiClient":
        """Create a scoped API client for a different Teams service URL."""
        return self.clone(service_url=service_url)

    def from_agentic_user(self, agentic_user: AgenticUser) -> "ApiClient":
        """Create a scoped API client for an agentic user."""
        return self.clone(agentic_user=agentic_user)

    def for_agentic_user(self, agentic_user: AgenticUser) -> "ApiClient":
        """Alias for from_agentic_user."""
        return self.from_agentic_user(agentic_user)

    def _scope_conversations(
        self,
        service_url: str | None,
        agentic_user: AgenticUser | None,
    ) -> ConversationClient:
        return self.clone(service_url=service_url, agentic_user=agentic_user).conversations

    def _get_scoped_http(self, agentic_user: AgenticUser | None) -> HttpClient:
        if self._auth_provider is None:
            return self._http.clone(share_http=True)

        return self._http.clone(
            ClientOptions(token=self._create_auth_provider_token(agentic_user)),
            share_http=True,
        )

    def _apply_auth_provider_token(self) -> None:
        if self._auth_provider is None:
            return

        self._http = self._get_scoped_http(self._default_agentic_user)

    def _create_auth_provider_token(self, agentic_user: AgenticUser | None) -> Token:
        auth_provider = self._auth_provider
        if auth_provider is None:
            return None

        async def resolve_auth_provider_token() -> str | StringLike | None:
            with get_tracer().start_as_current_span(
                API_SPAN_NAMES.auth_outbound,
                kind=SpanKind.CLIENT,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                flow = API_AUTH_FLOWS.agentic_user if agentic_user is not None else API_AUTH_FLOWS.app_only
                span.set_attribute(API_ATTRIBUTE_NAMES.auth_flow, flow)
                try:
                    token = auth_provider.token(agentic_user=agentic_user)
                    if inspect.isawaitable(token):
                        return await token
                    return token
                except Exception as exception:
                    record_exception(span, exception)
                    raise

        return resolve_auth_provider_token

    @property
    def http(self) -> HttpClient:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: HttpClient) -> None:
        """Set the HTTP client instance and propagate to all sub-clients."""
        self._http = value
        self._apply_auth_provider_token()
        ensure_outbound_telemetry_middleware(self._http)
        self._bots.http = self._http
        self.conversations.http = self._http
        self.users.http = self._http
        self.teams.http = self._http
        self.meetings.http = self._http
        if self._reactions is not None:
            self._reactions.http = self._http
