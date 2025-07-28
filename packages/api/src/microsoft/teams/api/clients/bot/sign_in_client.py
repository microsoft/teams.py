"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union, cast

from microsoft.teams.common.http import Client, ClientOptions

from ...models import SignInUrlResponse
from ..base_client import BaseClient
from .params import GetBotSignInResourceParams, GetBotSignInUrlParams


class BotSignInClient(BaseClient):
    """Client for managing bot sign-in."""

    def __init__(self, options: Union[Client, ClientOptions, None] = None) -> None:
        """Initialize the bot sign-in client.

        Args:
            options: Optional Client or ClientOptions instance.
        """
        super().__init__(options)

    async def get_url(self, params: GetBotSignInUrlParams) -> str:
        """Get a sign-in URL.

        Args:
            params: The parameters for getting the sign-in URL.

        Returns:
            The sign-in URL as a string.
        """
        res = await self.http.get(
            "https://token.botframework.com/api/botsignin/GetSignInUrl",
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
            "https://token.botframework.com/api/botsignin/GetSignInResource",
            params=params.model_dump(),
        )
        return SignInUrlResponse.model_validate(res.json())
