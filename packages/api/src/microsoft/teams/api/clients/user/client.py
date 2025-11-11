"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

from ..api_client_settings import ApiClientSettings, merge_api_client_settings
from ..base_client import BaseClient
from .token_client import UserTokenClient


class UserClient(BaseClient):
    """Client for managing Teams users."""

    def __init__(
        self,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """
        Initialize the UserClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(options)
        self._api_client_settings = merge_api_client_settings(api_client_settings)
        self.token = UserTokenClient(self.http, self._api_client_settings)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance and propagate to sub-clients."""
        self._http = value
        self.token.http = value
