"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime
from typing import Any, Optional, Union

from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.api.models.token.response import TokenResponse


class DirectTokenCredential(TokenCredential):
    """
    Azure Core TokenCredential implementation using direct tokens.

    """

    def __init__(self, token: Union[str, TokenResponse], connection_name: Optional[str] = None) -> None:
        """
        Initialize the direct token credential.

        Args:
            token: The access token (string) or TokenResponse object
            connection_name: OAuth connection name for logging/tracking purposes
        """
        self._token = token
        self._connection_name = connection_name
        self._cached_access_token: Optional[AccessToken] = None

    def get_token(
        self, *scopes: str, claims: Optional[str] = None, tenant_id: Optional[str] = None, **kwargs: Any
    ) -> AccessToken:
        """
        Retrieve an access token for Microsoft Graph.

        Args:
            *scopes: The scopes for which the token is being requested (ignored - token is pre-authorized)
            claims: Additional claims to include in the token request (ignored)
            tenant_id: The tenant ID (ignored - determined by token)
            **kwargs: Additional keyword arguments

        Returns:
            AccessToken: The access token for Microsoft Graph

        Raises:
            ClientAuthenticationError: If the token is invalid or expired
        """
        try:
            # Check if we have a valid cached access token
            if self._cached_access_token and self._is_token_valid(self._cached_access_token):
                return self._cached_access_token

            # Extract token string and expiration
            if isinstance(self._token, TokenResponse):
                token_string = self._token.token
                expires_on = self._parse_expiration(self._token.expiration)
            else:
                # Handle string tokens
                token_string = str(self._token)
                # For string tokens, assume 1-hour validity as fallback
                expires_on = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

            if not token_string:
                raise ClientAuthenticationError("Token string is empty or None")

            # Create access token
            access_token = AccessToken(token=token_string, expires_on=int(expires_on.timestamp()))

            # Cache for reuse
            self._cached_access_token = access_token

            return access_token

        except Exception as e:
            if isinstance(e, ClientAuthenticationError):
                raise
            raise ClientAuthenticationError(f"Failed to create access token: {str(e)}") from e

    def _parse_expiration(self, expiration: Optional[str]) -> datetime.datetime:
        """
        Parse expiration time from TokenResponse.

        Args:
            expiration: Expiration string from TokenResponse

        Returns:
            datetime: Parsed expiration time or fallback time
        """
        if not expiration:
            # Default to 1 hour if no expiration provided
            return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

        try:
            # Handle ISO format with Z suffix
            if expiration.endswith("Z"):
                expiration = expiration.replace("Z", "+00:00")

            # Handle epoch timestamp (if it's a number string)
            if expiration.isdigit():
                return datetime.datetime.fromtimestamp(int(expiration), tz=datetime.timezone.utc)

            # Parse as ISO format datetime
            return datetime.datetime.fromisoformat(expiration)

        except (ValueError, AttributeError):
            # If parsing fails, log and use default expiration
            # In a real scenario, you might want to log this
            return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)

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

        # Add 5-minute buffer before expiration
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        return token.expires_on > (now + 300)  # 5 minutes buffer
