"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft.teams.common.http import Client as HttpClient
from microsoft.teams.common.http import ClientOptions

from .clients import BotClient, ConversationClient, MeetingClient, TeamClient, UserClient


class Client:
    """Unified client for Microsoft Teams API operations."""

    def __init__(self, service_url: str, options: Optional[Union[HttpClient, ClientOptions]] = None) -> None:
        """Initialize the unified Teams API client.

        Args:
            service_url: The Teams service URL for API calls.
            options: Either an HTTP client instance or client options. If None, a default client is created.
        """
        self.service_url = service_url

        # Initialize HTTP client
        if options is None:
            self._http = HttpClient(ClientOptions(headers={"Content-Type": "application/json"}))
        elif isinstance(options, HttpClient):
            self._http = options
        else:
            # Ensure Content-Type header is set
            headers = options.headers or {}
            headers.setdefault("Content-Type", "application/json")
            options.headers = headers
            self._http = HttpClient(options)

        # Initialize all client types
        self.bots = BotClient(self._http)
        self.users = UserClient(self._http)
        self.conversations = ConversationClient(service_url, self._http)
        self.teams = TeamClient(service_url, self._http)
        self.meetings = MeetingClient(service_url, self._http)

    @property
    def http(self) -> HttpClient:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: HttpClient) -> None:
        """Set the HTTP client instance and propagate to all sub-clients."""
        self.bots.http = value
        self.conversations.http = value
        self.users.http = value
        self.teams.http = value
        self.meetings.http = value
        self._http = value
