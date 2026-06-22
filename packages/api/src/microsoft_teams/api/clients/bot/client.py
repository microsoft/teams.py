"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Optional, Union

from microsoft_teams.common.http import Client, ClientOptions

from ...auth.cloud_environment import PUBLIC, CloudEnvironment
from ..api_client_settings import ApiClientSettings, merge_api_client_settings
from ..base_client import BaseClient
from .sign_in_client import BotSignInClient
from .token_client import BotTokenClient


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
        self._cloud = cloud or PUBLIC
        merged_settings = merge_api_client_settings(api_client_settings, self._cloud)
        super().__init__(options, merged_settings)
        self.token = BotTokenClient(self.http, self._api_client_settings, cloud=self._cloud)
        self.sign_in = BotSignInClient(self.http, self._api_client_settings, cloud=self._cloud)

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
