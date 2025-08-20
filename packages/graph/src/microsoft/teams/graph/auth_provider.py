"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime
from typing import Any, Callable, Optional

from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import ClientAuthenticationError

from .protocols import TokenProtocol


class DirectTokenCredential(TokenCredential):
    """
    Azure Core TokenCredential implementation using direct tokens.

    """

    def __init__(self, token_callable: Callable[[], TokenProtocol], connection_name: Optional[str] = None) -> None:
        """
        Initialize the direct token credential.

        Args:
            token_callable: A callable that returns token data with expiration info
            connection_name: OAuth connection name
        """
        self._token_callable = token_callable
        self._connection_name = connection_name
        self._cached_access_token: Optional[AccessToken] = None

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        """
        Retrieve an access token for Microsoft Graph.

        Args:
            *scopes: Token scopes (required for interface compatibility)
            **kwargs: Additional keyword arguments (unused)

        Returns:
            AccessToken: The access token for Microsoft Graph

        Raises:
            ClientAuthenticationError: If the token is invalid or expired
        """
        try:
            # Check if we have a valid cached access token
            if self._cached_access_token and self._is_token_valid(self._cached_access_token):
                return self._cached_access_token

            # Get fresh token data from the callable
            try:
                token_data = self._token_callable()
            except Exception as e:
                raise ClientAuthenticationError(f"Failed to retrieve token from callable: {str(e)}") from e

            # Validate token data
            if not hasattr(token_data, "access_token"):
                raise ClientAuthenticationError("Token callable must return an object with 'access_token' attribute")

            if not token_data.access_token:
                raise ClientAuthenticationError("Token data is missing access_token")

            # Check for whitespace-only tokens
            if not token_data.access_token.strip():
                raise ClientAuthenticationError("Token data contains only whitespace")

            # Use provided expiration time or default to 1 hour
            if token_data.expires_at:
                expires_on = int(token_data.expires_at.timestamp())
            else:
                # Fallback if no expiration provided
                fallback_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                expires_on = int(fallback_expiry.timestamp())

            access_token = AccessToken(token=token_data.access_token, expires_on=expires_on)

            # Cache for reuse
            self._cached_access_token = access_token

            return access_token

        except Exception as e:
            if isinstance(e, ClientAuthenticationError):
                raise
            raise ClientAuthenticationError(f"Failed to create access token: {str(e)}") from e

    def _is_token_valid(self, token: AccessToken) -> bool:
        """
        Check if a cached access token is still valid.

        Args:
            token: The access token to check

        Returns:
            bool: True if the token is valid and not expired
        """
        if not token or not token.token:
            return False

        # Use exact expiration time - no buffer
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        return token.expires_on > now


__all__ = [
    "DirectTokenCredential",
    "TokenProtocol",
]
