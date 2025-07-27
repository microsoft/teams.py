"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict, List, Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

from ...models import TokenResponse, TokenStatus
from ..base_client import BaseClient
from .params import (
    ExchangeUserTokenParams,
    GetUserAADTokenParams,
    GetUserTokenParams,
    GetUserTokenStatusParams,
    SignOutUserParams,
)


class UserTokenClient(BaseClient):
    """Client for managing user tokens in Teams."""

    def __init__(self, options: Optional[Union[Client, ClientOptions]] = None) -> None:
        """
        Initialize the UserTokenClient.

        Args:
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
        """
        super().__init__(options)

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
            "https://token.botframework.com/api/usertoken/GetToken",
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
            "https://token.botframework.com/api/usertoken/GetAadTokens",
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
            "https://token.botframework.com/api/usertoken/GetTokenStatus",
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
            "https://token.botframework.com/api/usertoken/SignOut",
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
            "https://token.botframework.com/api/usertoken/exchange",
            params=query_params,
            json=params.exchange_request.model_dump(),
        )
        return TokenResponse.model_validate(response.json())
