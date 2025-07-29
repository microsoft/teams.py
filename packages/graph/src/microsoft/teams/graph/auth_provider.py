"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Optional

from azure.core.credentials import AccessToken, TokenCredential

if TYPE_CHECKING:
    from microsoft.teams.app.routing import ActivityContext


class TeamsContextAuthProvider(TokenCredential):
    """Bridges Teams SDK authentication with Microsoft Graph SDK."""

    def __init__(self, context: "ActivityContext") -> None:
        """Initialize the auth provider with a Teams SDK context.

        Args:
            context: The Teams SDK ActivityContext containing user tokens
        """
        self._context = context
        self._cached_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        """Get access token for Graph API calls.

        This is the sync version required by Azure Identity interface.
        For POC, we use a simple sync approach.

        Args:
            *scopes: The scopes for which to get the token
            **kwargs: Additional keyword arguments

        Returns:
            AccessToken object with token and expiry

        Raises:
            ValueError: If user is not signed in or no token available
        """
        if self._is_token_valid():
            return AccessToken(self._cached_token, self._token_expiry)

        # Get token from Teams context
        user_token = self._context.user_graph_token
        if not user_token:
            raise ValueError("User must be signed in to access Graph API")

        # Cache the token
        self._cached_token = str(user_token)
        self._token_expiry = user_token.token.valid_to

        return AccessToken(self._cached_token, self._token_expiry)

    def _is_token_valid(self) -> bool:
        """Check if cached token is still valid.

        Returns:
            True if token is valid and not expiring soon, False otherwise
        """
        if not self._cached_token or not self._token_expiry:
            return False

        # Add 5-minute buffer before expiry to avoid race conditions
        buffer_time = timedelta(minutes=5)
        return datetime.utcnow() + buffer_time < self._token_expiry
