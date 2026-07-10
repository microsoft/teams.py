"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

from microsoft_teams.common.http import Client, ClientOptions
from typing_extensions import deprecated

from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient
from .sign_in_client import BotSignInClient
from .token_client import BotTokenClient

if TYPE_CHECKING:
    from ...auth.cloud_environment import CloudEnvironment


@deprecated("The bot client is deprecated and will be removed in a future release.")
class BotClient(BaseClient):
    """Client for managing bot operations."""

    def __init__(
        self,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        cloud: Optional[CloudEnvironment] = None,
    ) -> None:
        """Initialize the BotClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
            cloud: Optional cloud environment for sovereign cloud support.
        """
        super().__init__(options, api_client_settings)
        self.token = BotTokenClient(self.http, self._api_client_settings, cloud=cloud)
        self.sign_in = BotSignInClient(self.http, self._api_client_settings)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance and propagate to sub-clients."""
        self._http = value
        self.token.http = value
        self.sign_in.http = value
