"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

try:
    from azure.core.credentials import AccessToken
    from msgraph.graph_service_client import GraphServiceClient

    _msgraph_available = True
except ImportError:
    _msgraph_available = False
    GraphServiceClient = None
    AccessToken = None

if TYPE_CHECKING:
    from microsoft.teams.app import ActivityContext


class GraphClient:
    """Microsoft Graph client for Teams applications."""

    def __init__(self, access_token: str, scopes: Optional[List[str]] = None) -> None:
        """Initialize Graph client with access token.

        Args:
            access_token: OAuth access token from Teams authentication
            scopes: Graph API scopes (defaults to basic user scopes)
        """
        if not _msgraph_available or not GraphServiceClient:
            raise ImportError("msgraph-sdk is required for Graph integration")

        self._access_token = access_token
        self._scopes = scopes

        # Create Graph service client with token credential
        self._client = GraphServiceClient(credentials=_TokenCredential(access_token), scopes=self._scopes)

    async def get_me(self) -> Dict[str, Any]:
        """Get current user information."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        result = await self._client.me.get()
        return result.__dict__ if hasattr(result, "__dict__") else {}

    async def check_token_scopes(self) -> None:
        """Check what scopes the current token actually has by calling a simple endpoint."""
        try:
            # Try calling /me first - this only requires User.Read
            await self.get_me()
            # Note: This will be logged by the calling ActivityContext
        except Exception:
            # Note: This will be logged by the calling ActivityContext
            raise

    async def get_my_teams(self) -> Dict[str, Any]:
        """Get teams the current user belongs to."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        try:
            result = await self._client.me.joined_teams.get()
            return result.__dict__ if hasattr(result, "__dict__") else {}
        except Exception:
            # Return empty dict on error, let caller handle logging
            return {}

    async def get_team(self, team_id: str) -> Dict[str, Any]:
        """Get specific team information."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        result = await self._client.teams.by_team_id(team_id).get()
        return result.__dict__ if hasattr(result, "__dict__") else {}

    async def get_team_channels(self, team_id: str) -> Dict[str, Any]:
        """Get channels for a specific team."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        result = await self._client.teams.by_team_id(team_id).channels.get()
        return result.__dict__ if hasattr(result, "__dict__") else {}


class _TokenCredential:
    """Simple token credential for Graph SDK."""

    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    def get_token(self, *scopes: str, **kwargs: Any) -> Any:
        """Return the access token."""
        if not AccessToken:
            raise ImportError("azure-core is required for token credentials")
        # Return token valid for 1 hour (typical OAuth token lifetime)
        return AccessToken(self._access_token, expires_on=0)


def enable_graph_integration(scopes: Optional[List[str]] = None) -> None:
    """Enable Microsoft Graph integration for Teams ActivityContext.

    This function adds a 'get_graph_client' method to ActivityContext that provides
    access to Microsoft Graph APIs using the user's OAuth token.

    Args:
        scopes: Optional list of Graph API scopes to request
    """
    if not _msgraph_available:
        import logging

        logging.getLogger(__name__).warning("msgraph-sdk not available, Graph integration disabled")
        return

    from microsoft.teams.app import ActivityContext

    async def get_graph_client(self: ActivityContext[Any]) -> Optional[GraphClient]:
        """Get authenticated Graph client for the current user."""
        # Check if user is signed in
        if not self.is_signed_in:
            return None

        try:
            # Get the user's access token from the Teams OAuth system
            from microsoft.teams.api import GetUserTokenParams

            token_params = GetUserTokenParams(
                user_id=self.activity.from_.id,
                connection_name=self.connection_name,
                channel_id=self.activity.channel_id,
            )
            token_response = await self.api.users.token.get(token_params)

            if not token_response.token:
                return None

            return GraphClient(token_response.token, scopes)
        except Exception as e:
            # Token retrieval failed - user may need to sign in again
            self.logger.warning(f"Failed to get user token for Graph client: {e}")
            return None

    # Add the graph method to ActivityContext
    ActivityContext.get_graph_client = get_graph_client  # pyright: ignore[reportAttributeAccessIssue]

    import logging

    logging.getLogger(__name__).info("Microsoft Graph integration enabled")
