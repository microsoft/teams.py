"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import datetime
from typing import Any, Optional

from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.api.clients.user.params import GetUserTokenParams
from microsoft.teams.app.routing.activity_context import ActivityContext


class TeamsTokenCredential(TokenCredential):
    """
    Azure Core TokenCredential implementation that bridges Teams OAuth tokens
    with Microsoft Graph SDK authentication requirements.

    This credential obtains access tokens through the Teams Bot Framework Token Service,
    leveraging the existing OAuth flow configured in the Teams application.
    """

    def __init__(self, context: "ActivityContext[Any]", connection_name: Optional[str] = None) -> None:
        """
        Initialize the Teams token credential.

        Args:
            context: The Teams activity context containing user and API client information
            connection_name: OAuth connection name (defaults to context.connection_name)
        """
        self._context = context
        self._connection_name = connection_name or context.connection_name
        self._cached_token: Optional[AccessToken] = None

    def get_token(
        self, *scopes: str, claims: Optional[str] = None, tenant_id: Optional[str] = None, **kwargs: Any
    ) -> AccessToken:
        """
        Retrieve an access token for Microsoft Graph.

        Args:
            *scopes: The scopes for which the token is being requested
            claims: Additional claims to include in the token request
            tenant_id: The tenant ID (ignored - determined by Teams context)
            **kwargs: Additional keyword arguments

        Returns:
            AccessToken: The access token for Microsoft Graph

        Raises:
            ClientAuthenticationError: If authentication fails or user is not signed in
        """
        try:
            # Check if we have a cached token that's still valid
            if self._cached_token and self._is_token_valid(self._cached_token):
                return self._cached_token

            # Get or create event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Run the async token retrieval
            token_response = loop.run_until_complete(self._get_token_async())

            # Use actual token expiration from response
            expires_on = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)  # Default fallback
            if token_response.expiration:
                try:
                    # Parse the expiration from token response
                    expires_on = datetime.datetime.fromisoformat(token_response.expiration.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    # If parsing fails, use default expiration
                    pass

            access_token = AccessToken(token=token_response.token, expires_on=int(expires_on.timestamp()))

            # Cache the token for future use
            self._cached_token = access_token

            return access_token

        except Exception as e:
            # Check if user needs to sign in
            if not self._context.is_signed_in:
                raise ClientAuthenticationError(
                    "User is not signed in. Call 'await context.sign_in()' first to authenticate the user."
                ) from e

            # Re-raise as authentication error with context
            raise ClientAuthenticationError(f"Failed to obtain access token for Microsoft Graph: {str(e)}") from e

    async def _get_token_async(self):
        """Async helper to get token from Teams API."""
        token_params = GetUserTokenParams(
            channel_id=self._context.activity.channel_id,
            user_id=self._context.activity.from_.id,
            connection_name=self._connection_name,
        )
        return await self._context.api.users.token.get(token_params)

    def _is_token_valid(self, token: AccessToken) -> bool:
        """
        Check if a cached token is still valid.

        Args:
            token: The access token to check

        Returns:
            bool: True if the token is valid and not expired
        """
        if not token or not token.token:
            return False

        # Add 5-minute buffer before expiration
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        return token.expires_on > (now + 300)  # 5 minutes buffer
