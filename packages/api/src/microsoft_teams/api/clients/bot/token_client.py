"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Literal, Optional, Union, cast

from microsoft_teams.api.auth.credentials import ClientCredentials
from microsoft_teams.common.http import Client, ClientOptions
from pydantic import BaseModel

from ...auth import Credentials, TokenCredentials, TokenProviderProtocol, TokenResult
from ...auth.cloud_environment import PUBLIC
from ..api_client_settings import ApiClientSettings, merge_api_client_settings
from ..base_client import BaseClient

if TYPE_CHECKING:
    from ...auth.cloud_environment import CloudEnvironment


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
    """Deprecated client for managing bot tokens.

    Token minting for Teams apps now happens through the MSAL-backed TokenManager
    in microsoft-teams-apps.
    """

    def __init__(
        self,
        options: Union[Client, ClientOptions, None] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        cloud: Optional[CloudEnvironment] = None,
    ) -> None:
        """Initialize the bot token client.

        Args:
            options: Optional Client or ClientOptions instance.
            api_client_settings: Optional API client settings.
            cloud: Optional cloud environment for sovereign cloud support.
        """
        self._cloud = cloud or PUBLIC
        merged_settings = merge_api_client_settings(api_client_settings, self._cloud)
        super().__init__(options, merged_settings)

    async def get(self, credentials: Credentials) -> GetBotTokenResponse:
        """Get a bot token.

        Args:
            credentials: The credentials to use for authentication.

        Returns:
            The bot token response.
        """
        if isinstance(credentials, TokenCredentials):
            token = await self._get_token_provider_value(credentials, self._cloud.bot_scope)

            return GetBotTokenResponse(
                token_type="Bearer",
                expires_in=-1,
                access_token=token,
            )

        assert isinstance(credentials, ClientCredentials), (
            "Bot token client currently only supports Credentials with secrets."
        )

        tenant_id = credentials.tenant_id or self._cloud.login_tenant
        res = await self.http.post(
            f"{self._cloud.login_endpoint}/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scope": self._cloud.bot_scope,
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
            token = await self._get_token_provider_value(credentials, self._cloud.graph_scope)

            return GetBotTokenResponse(
                token_type="Bearer",
                expires_in=-1,
                access_token=token,
            )

        assert isinstance(credentials, ClientCredentials), (
            "Bot token client currently only supports Credentials with secrets."
        )

        tenant_id = credentials.tenant_id or self._cloud.login_tenant
        res = await self.http.post(
            f"{self._cloud.login_endpoint}/{tenant_id}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scope": self._cloud.graph_scope,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        return GetBotTokenResponse.model_validate(res.json())

    async def _get_token_provider_value(self, credentials: TokenCredentials, scope: str) -> str:
        result = self._call_token_provider(credentials, scope)
        token = await result if inspect.isawaitable(result) else result
        if token is None:
            raise ValueError("Token provider returned no app token.")
        return str(token)

    def _call_token_provider(self, credentials: TokenCredentials, scope: str) -> TokenResult:
        token_provider = cast(Any, credentials.token)
        if isinstance(token_provider, TokenProviderProtocol):
            return token_provider.get_app_token(scope, credentials.tenant_id)

        try:
            parameters = list(inspect.signature(token_provider).parameters.values())
        except (TypeError, ValueError):
            return cast(TokenResult, token_provider(scope, credentials.tenant_id))

        accepts_agentic_user = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD or parameter.name == "agentic_user"
            for parameter in parameters
        )
        if accepts_agentic_user:
            return cast(TokenResult, token_provider(scope, credentials.tenant_id, agentic_user=None))

        positional_parameters = [
            parameter
            for parameter in parameters
            if parameter.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        required_positional_parameters = [
            parameter for parameter in positional_parameters if parameter.default is inspect.Parameter.empty
        ]
        if len(required_positional_parameters) >= 3:
            return cast(TokenResult, token_provider(scope, credentials.tenant_id, None))

        return cast(TokenResult, token_provider(scope, credentials.tenant_id))
