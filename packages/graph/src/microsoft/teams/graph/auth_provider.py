"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import concurrent.futures
import datetime
from typing import Any, Optional

from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.common.http.client_token import Token, resolve_token


class DirectTokenCredential(TokenCredential):
    """
    Azure Core TokenCredential implementation using direct tokens.
    """

    def __init__(self, token: Token, connection_name: Optional[str] = None) -> None:
        """
        Initialize the direct token credential.

        Args:
            token: Token data (string, StringLike, callable, or None)
            connection_name: OAuth connection name for logging/tracking purposes
        """
        self._token = token
        self._connection_name = connection_name

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        """
        Retrieve an access token for Microsoft Graph.

        Args:
            *scopes: Token scopes (required for interface compatibility)
            **kwargs: Additional keyword arguments (unused)

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
                    token_str = future.result(timeout=30.0)
            except RuntimeError:
                token_str = asyncio.run(resolve_token(self._token))

            if not token_str:
                raise ClientAuthenticationError("Token resolved to None or empty string")

            if not token_str.strip():
                raise ClientAuthenticationError("Token contains only whitespace")

            # Default expiration to 1 hour from now
            expires_on = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).timestamp())

            return AccessToken(token=token_str, expires_on=expires_on)

        except Exception as e:
            if isinstance(e, ClientAuthenticationError):
                raise
            raise ClientAuthenticationError(f"Failed to resolve token: {str(e)}") from e


__all__ = [
    "DirectTokenCredential",
]
