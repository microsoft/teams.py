"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft.teams.common.http import Client, ClientOptions


class BaseClient:
    """Base client"""

    def __init__(self, options: Optional[Union[Client, ClientOptions]] = None) -> None:
        """Initialize the BaseClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
        """
        if options is None:
            self._http = Client(ClientOptions())
        elif isinstance(options, Client):
            self._http = options
        else:
            self._http = Client(options)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance."""
        self._http = value
