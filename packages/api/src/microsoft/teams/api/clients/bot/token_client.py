"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from typing import Literal, Optional, Union

from microsoft.teams.common.http import Client, ClientOptions
from pydantic import BaseModel

from ...auth import Credentials, TokenCredentials
from ..base_client import BaseClient


class GetBotTokenResponse(BaseModel):
    """Response model for bot token requests."""

    # Note: These fields use snake_case to match TypeScript exactly
    token_type: Literal["Bearer"]
    """
    The token type.
    """
    expires_in: int
    """
    The token expiration time in seconds.
    """
    ext_expires_in: Optional[int] = None
    """
    The extended token expiration time in seconds.
    """
    access_token: str
    """
    The access token.
    """


class BotTokenClient(BaseClient):
    """Client for managing bot tokens."""

    def __init__(self, options: Union[Client, ClientOptions, None] = None) -> None:
        """Initialize the bot token client.

        Args:
            options: Optional Client or ClientOptions instance.
        """
        super().__init__(options)

    async def get(self, credentials: Credentials) -> GetBotTokenResponse:
        """Get a bot token.

        Args:
            credentials: The credentials to use for authentication.

        Returns:
            The bot token response.
        """
        if isinstance(credentials, TokenCredentials):
            token = credentials.token(
                "https://api.botframework.com/.default",
                credentials.tenant_id,
            )
            if inspect.isawaitable(token):
                token = await token

            return GetBotTokenResponse(
                token_type="Bearer",
                expires_in=-1,
                access_token=token,
            )

        tenant_id = credentials.tenant_id or "botframework.com"
        res = await self.http.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scope": "https://api.botframework.com/.default",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        return GetBotTokenResponse.model_validate(res.json())

    async def get_graph(self, credentials: Credentials) -> GetBotTokenResponse:
        """Get a bot token for Microsoft Graph.

        Args:
            credentials: The credentials to use for authentication.

        Returns:
            The bot token response.
        """
        if isinstance(credentials, TokenCredentials):
            token = credentials.token(
                "https://graph.microsoft.com/.default",
                credentials.tenant_id,
            )
            if inspect.isawaitable(token):
                token = await token

            return GetBotTokenResponse(
                token_type="Bearer",
                expires_in=-1,
                access_token=token,
            )

        tenant_id = credentials.tenant_id or "botframework.com"
        res = await self.http.post(
            f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        return GetBotTokenResponse.model_validate(res.json())
