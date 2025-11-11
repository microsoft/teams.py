"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union, cast

from microsoft.teams.common.http import Client, ClientOptions

from ...models import SignInUrlResponse
from ..api_client_settings import ApiClientSettings, merge_api_client_settings
from ..base_client import BaseClient
from .params import GetBotSignInResourceParams, GetBotSignInUrlParams

# Bot sign-in API endpoints
BOT_SIGNIN_ENDPOINTS = {
    "URL": "api/botsignin/GetSignInUrl",
    "RESOURCE": "api/botsignin/GetSignInResource",
}


class BotSignInClient(BaseClient):
    """Client for managing bot sign-in."""

    def __init__(
        self,
        options: Union[Client, ClientOptions, None] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """Initialize the bot sign-in client.

        Args:
            options: Optional Client or ClientOptions instance.
            api_client_settings: Optional API client settings for configuring OAuth endpoints.
        """
        super().__init__(options)
        self._api_client_settings = merge_api_client_settings(api_client_settings)

    async def get_url(self, params: GetBotSignInUrlParams) -> str:
        """Get a sign-in URL.

        Args:
            params: The parameters for getting the sign-in URL.

        Returns:
            The sign-in URL as a string.
        """
        res = await self.http.get(
            f"{self._api_client_settings.oauth_url}/{BOT_SIGNIN_ENDPOINTS['URL']}",
            params=params.model_dump(),
        )
        return cast(str, res.text)  # type: ignore[redundant-cast]

    async def get_resource(self, params: GetBotSignInResourceParams) -> SignInUrlResponse:
        """Get a sign-in resource.

        Args:
            params: The parameters for getting the sign-in resource.

        Returns:
            The sign-in resource response.
        """
        res = await self.http.get(
            f"{self._api_client_settings.oauth_url}/{BOT_SIGNIN_ENDPOINTS['RESOURCE']}",
            params=params.model_dump(),
        )
        return SignInUrlResponse.model_validate(res.json())
