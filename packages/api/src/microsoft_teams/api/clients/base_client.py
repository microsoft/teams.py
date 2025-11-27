"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft_teams.common.http import Client, ClientOptions

from .api_client_settings import ApiClientSettings, merge_api_client_settings


class BaseClient:
    """Base client"""

    def __init__(
        self,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """Initialize the BaseClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        if options is None:
            self._http = Client(ClientOptions())
        elif isinstance(options, Client):
            self._http = options
        else:
            self._http = Client(options)

        self._api_client_settings = merge_api_client_settings(api_client_settings)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance."""
        self._http = value
