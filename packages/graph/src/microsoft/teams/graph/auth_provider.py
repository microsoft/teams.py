"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import concurrent.futures
import datetime
import logging
from typing import Any

import jwt
from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.common.http.client_token import Token, resolve_token

logger = logging.getLogger(__name__)


class AuthProvider(TokenCredential):
    """
    Provides authentication for Microsoft Graph using Teams tokens.

    """

    def __init__(self, token: Token) -> None:
        """
        Initialize the AuthProvider.

        Args:
            token: Token data (string, StringLike, callable, or None)
        """
        self._token = token

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        """
        Retrieve an access token for Microsoft Graph.

        Args:
            *scopes: Token scopes (required for interface compatibility)
            **kwargs: Additional keyword arguments

        Returns:
            AccessToken: The access token for Microsoft Graph

        Raises:
            ClientAuthenticationError: If the token is invalid or authentication fails
        """
        try:
            # Resolve the token using the common utility
            try:
                asyncio.get_running_loop()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, resolve_token(self._token))
                    token_str = future.result()
            except RuntimeError:
                token_str = asyncio.run(resolve_token(self._token))

            if not token_str:
                raise ClientAuthenticationError("Token resolved to None or empty string")

            if not token_str.strip():
                raise ClientAuthenticationError("Token contains only whitespace")

            # Try to extract expiration from JWT, fallback to 1 hour default
            try:
                # Decode JWT without verification to extract expiration
                payload = jwt.decode(token_str, algorithms=["RS256"], options={"verify_signature": False})
                expires_on = payload.get("exp")
                if not expires_on:
                    # Fallback to 1 hour from now if no exp claim
                    logger.debug("JWT token missing 'exp' claim, using 1-hour default expiration")
                    now = datetime.datetime.now(datetime.timezone.utc)
                    expires_on = int((now + datetime.timedelta(hours=1)).timestamp())
            except Exception:
                # Fallback to 1 hour from now if JWT decoding fails (e.g., not a JWT)
                logger.debug("Token is not a valid JWT, using 1-hour default expiration")
                now = datetime.datetime.now(datetime.timezone.utc)
                expires_on = int((now + datetime.timedelta(hours=1)).timestamp())

            return AccessToken(token=token_str, expires_on=expires_on)

        except Exception as e:
            if isinstance(e, ClientAuthenticationError):
                raise
            raise ClientAuthenticationError(f"Failed to resolve token: {str(e)}") from e
