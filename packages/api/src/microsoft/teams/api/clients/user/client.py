"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

from ..base_client import BaseClient
from .token_client import UserTokenClient


class UserClient(BaseClient):
    """Client for managing Teams users."""

    def __init__(self, options: Optional[Union[Client, ClientOptions]] = None) -> None:
        """
        Initialize the UserClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
        """
        super().__init__(options)

        self.token = UserTokenClient(self.http)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance and propagate to sub-clients."""
        self._http = value
        self.token.http = value
