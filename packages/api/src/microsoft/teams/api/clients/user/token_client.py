"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict, List, Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

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

# User token API endpoints
USER_TOKEN_ENDPOINTS = {
    "GET_TOKEN": "api/usertoken/GetToken",
    "GET_AAD_TOKENS": "api/usertoken/GetAadTokens",
    "GET_STATUS": "api/usertoken/GetTokenStatus",
    "SIGN_OUT": "api/usertoken/SignOut",
    "EXCHANGE": "api/usertoken/exchange",
}


class UserTokenClient(BaseClient):
    """Client for managing user tokens in Teams."""

    def __init__(
        self,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """
        Initialize the UserTokenClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(options)
        self._api_client_settings = merge_api_client_settings(api_client_settings)

    async def get(self, params: GetUserTokenParams) -> TokenResponse:
        """
        Get a user token.

        Args:
            params: Parameters for getting the user token.

        Returns:
            TokenResponse containing the user token.
        """
        query_params = params.model_dump(exclude_none=True)
        response = await self.http.get(
            f"{self._api_client_settings.oauth_url}/{USER_TOKEN_ENDPOINTS['GET_TOKEN']}",
            params=query_params,
        )
        return TokenResponse.model_validate(response.json())

    async def get_aad(self, params: GetUserAADTokenParams) -> Dict[str, TokenResponse]:
        """
        Get AAD tokens for a user.

        Args:
            params: Parameters for getting AAD tokens.

        Returns:
            Dictionary mapping resource URLs to token responses.
        """
        query_params = params.model_dump(exclude_none=True)
        response = await self.http.post(
            f"{self._api_client_settings.oauth_url}/{USER_TOKEN_ENDPOINTS['GET_AAD_TOKENS']}",
            params=query_params,
        )
        data = response.json()
        return {k: TokenResponse.model_validate(v) for k, v in data.items()}

    async def get_status(self, params: GetUserTokenStatusParams) -> List[TokenStatus]:
        """
        Get token status for a user.

        Args:
            params: Parameters for getting token status.

        Returns:
            List of token statuses.
        """
        query_params = params.model_dump(exclude_none=True)
        response = await self.http.get(
            f"{self._api_client_settings.oauth_url}/{USER_TOKEN_ENDPOINTS['GET_STATUS']}",
            params=query_params,
        )
        return [TokenStatus.model_validate(item) for item in response.json()]

    async def sign_out(self, params: SignOutUserParams) -> None:
        """
        Sign out a user.

        Args:
            params: Parameters for signing out the user.
        """
        query_params = params.model_dump(exclude_none=True)
        await self.http.delete(
            f"{self._api_client_settings.oauth_url}/{USER_TOKEN_ENDPOINTS['SIGN_OUT']}",
            params=query_params,
        )

    async def exchange(self, params: ExchangeUserTokenParams) -> TokenResponse:
        """
        Exchange a user token.

        Args:
            params: Parameters for exchanging the token.

        Returns:
            TokenResponse containing the exchanged token.
        """
        query_params = {
            "userId": params.user_id,
            "connectionName": params.connection_name,
            "channelId": params.channel_id,
        }
        response = await self.http.post(
            f"{self._api_client_settings.oauth_url}/{USER_TOKEN_ENDPOINTS['EXCHANGE']}",
            params=query_params,
            json=params.exchange_request.model_dump(),
        )
        return TokenResponse.model_validate(response.json())
