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
from ..auth.credentials import (
    AgenticAppTokenProviderProtocol,
    AgenticUserTokenProviderProtocol,
    TokenProviderProtocol,
)
from ..diagnostics._constants import API_ATTRIBUTE_NAMES, API_AUTH_FLOWS, API_SPAN_NAMES
from ..diagnostics._helpers import get_tracer, record_exception
from ..diagnostics._outbound import ensure_outbound_telemetry_middleware
from ..models import AgenticIdentity
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
        token_provider: Optional[TokenProviderProtocol] = None,
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
        if token_provider is not None and self._http.token is not None:
            raise ValueError("Cannot use both a token provider and an HTTP client token.")

        self._token_provider = token_provider
        self._default_agentic_identity = agentic_identity
        self._apply_token_provider_token()

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
        if self._token_provider is not None:
            http.token = None

        return ApiClient(
            service_url or self.service_url,
            http,
            self._api_client_settings,
            cloud=self._cloud,
            token_provider=self._token_provider,
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

    def _scope_conversations(
        self,
        service_url: str | None,
        agentic_identity: AgenticIdentity | None,
    ) -> ConversationClient:
        return self.clone(service_url=service_url, agentic_identity=agentic_identity).conversations

    def _get_scoped_http(self, agentic_identity: AgenticIdentity | None) -> HttpClient:
        if self._token_provider is None:
            return self._http.clone(share_http=True)

        return self._http.clone(
            ClientOptions(token=self._create_token_provider_token(agentic_identity)),
            share_http=True,
        )

    def _apply_token_provider_token(self) -> None:
        if self._token_provider is None:
            return

        self._http = self._get_scoped_http(self._default_agentic_identity)

    def _create_token_provider_token(self, agentic_identity: AgenticIdentity | None) -> Token:
        token_provider = self._token_provider
        if token_provider is None:
            return None

        async def resolve_token_provider_token() -> str | StringLike | None:
            with get_tracer().start_as_current_span(
                API_SPAN_NAMES.auth_outbound,
                kind=SpanKind.CLIENT,
                record_exception=False,
                set_status_on_exception=False,
            ) as span:
                if agentic_identity is None:
                    flow = API_AUTH_FLOWS.app_only
                elif agentic_identity.agentic_user_id:
                    flow = API_AUTH_FLOWS.agentic_user
                else:
                    flow = API_AUTH_FLOWS.agentic_app
                span.set_attribute(API_ATTRIBUTE_NAMES.auth_flow, flow)
                try:
                    if agentic_identity is None:
                        token = token_provider.get_app_token(self._cloud.bot_scope, None)
                    elif agentic_identity.agentic_user_id:
                        if not agentic_identity.agentic_app_id:
                            raise ValueError("agentic_identity.agentic_app_id is required to get an agentic user token")
                        if not isinstance(token_provider, AgenticUserTokenProviderProtocol):
                            raise ValueError(
                                "This client is scoped to a user-backed AgenticIdentity, but the configured token "
                                "provider does not implement get_agentic_user_token. Falling back to an app-only "
                                "token would authenticate as the app rather than the user."
                            )
                        token = token_provider.get_agentic_user_token(
                            self._cloud.agent_bot_scope,
                            agentic_identity.agentic_app_id,
                            agentic_identity.agentic_user_id,
                            agentic_identity.tenant_id,
                        )
                    else:
                        if not agentic_identity.agentic_app_id:
                            raise ValueError("agentic_identity.agentic_app_id is required to get an agentic app token")
                        if not isinstance(token_provider, AgenticAppTokenProviderProtocol):
                            raise ValueError(
                                "This client is scoped to an AgenticIdentity, but the configured token provider does "
                                "not implement get_agentic_app_token. Falling back to an app-only token would "
                                "authenticate as the wrong app."
                            )
                        token = token_provider.get_agentic_app_token(
                            self._cloud.agent_bot_scope,
                            agentic_identity.agentic_app_id,
                            agentic_identity.tenant_id,
                        )
                    if inspect.isawaitable(token):
                        token = await token
                    return None if token is None else str(token)
                except Exception as exception:
                    record_exception(span, exception)
                    raise

        return resolve_token_provider_token

    @property
    def http(self) -> HttpClient:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: HttpClient) -> None:
        """Set the HTTP client instance and propagate to all sub-clients."""
        self._http = value
        self._apply_token_provider_token()
        ensure_outbound_telemetry_middleware(self._http)
        self._bots.http = self._http
        self.conversations.http = self._http
        self.users.http = self._http
        self.teams.http = self._http
        self.meetings.http = self._http
        if self._reactions is not None:
            self._reactions.http = self._http
