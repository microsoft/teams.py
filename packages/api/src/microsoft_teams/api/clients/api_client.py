"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from microsoft_teams.common import Client as HttpClient
from microsoft_teams.common import ClientOptions
from typing_extensions import deprecated

from .api_client_settings import ApiClientSettings
from .base_client import BaseClient
from .bot import BotClient  # pyright: ignore[reportDeprecated]
from .conversation import ConversationClient
from .meeting import MeetingClient
from .reaction import ReactionClient
from .team import TeamClient
from .user import UserClient

if TYPE_CHECKING:
    from ..auth.cloud_environment import CloudEnvironment


class ApiClient(BaseClient):
    """Unified client for Microsoft Teams API operations."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[HttpClient, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        cloud: Optional[CloudEnvironment] = None,
    ) -> None:
        """Initialize the unified Teams API client.

        Args:
            service_url: The Teams service URL for API calls.
            options: Either an HTTP client instance or client options. If None, a default client is created.
            api_client_settings: Optional API client settings.
            cloud: Optional cloud environment for sovereign cloud support.
        """
        super().__init__(options, api_client_settings)
        self.service_url = service_url.rstrip("/")

        # Initialize all client types
        self._bots = BotClient(  # pyright: ignore[reportDeprecated]
            self._http, self._api_client_settings, cloud=cloud
        )
        self.users = UserClient(self._http, self._api_client_settings)
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

    @property
    def http(self) -> HttpClient:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: HttpClient) -> None:
        """Set the HTTP client instance and propagate to all sub-clients."""
        self._bots.http = value
        self.conversations.http = value
        self.users.http = value
        self.teams.http = value
        self.meetings.http = value
        if self._reactions is not None:
            self._reactions.http = value
        self._http = value
