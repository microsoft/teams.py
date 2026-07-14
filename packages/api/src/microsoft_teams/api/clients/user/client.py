"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Union

from microsoft_teams.common.http import Client, ClientOptions
from typing_extensions import deprecated

from ...auth.cloud_environment import PUBLIC, CloudEnvironment
from ...models import TokenResponse, TokenStatus
from ..api_client_settings import ApiClientSettings, merge_api_client_settings
from ..base_client import BaseClient
from .params import (
    ExchangeUserTokenParams,
    GetUserAADTokenParams,
    GetUserTokenParams,
    GetUserTokenStatusParams,
    SignOutUserParams,
)
from .token_client import UserTokenClient


class UserClient(BaseClient):
    """Client for managing Teams users."""

    def __init__(
        self,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        *,
        cloud: Optional[CloudEnvironment] = None,
    ) -> None:
        """
        Initialize the UserClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        self._cloud = cloud or PUBLIC
        merged_settings = merge_api_client_settings(api_client_settings, self._cloud)
        super().__init__(options, merged_settings)
        self._token = UserTokenClient(self.http, self._api_client_settings, cloud=self._cloud)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance and propagate to sub-clients."""
        self._http = value
        self._token.http = value

    @property
    @deprecated(
        "Use the flattened methods on `UserClient` instead (e.g. `users.get_token(...)`). "
        "This grouped accessor will be removed in a future release."
    )
    def token(self) -> UserTokenClient:
        """Get the user token client."""
        return self._token

    async def get_token(self, params: GetUserTokenParams) -> TokenResponse:
        """Get a user token for the given connection."""
        return await self._token.get(params)

    async def get_aad_tokens(self, params: GetUserAADTokenParams) -> Dict[str, TokenResponse]:
        """Get AAD tokens for the given connection and resource urls."""
        return await self._token.get_aad(params)

    async def get_token_status(self, params: GetUserTokenStatusParams) -> List[TokenStatus]:
        """Get the token status for a user."""
        return await self._token.get_status(params)

    async def sign_out(self, params: SignOutUserParams) -> None:
        """Sign a user out of the given connection."""
        return await self._token.sign_out(params)

    async def exchange_token(self, params: ExchangeUserTokenParams) -> TokenResponse:
        """Exchange a user token for the given connection."""
        return await self._token.exchange(params)
