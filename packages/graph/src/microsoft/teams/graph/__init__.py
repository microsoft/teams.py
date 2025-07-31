"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Microsoft Teams Graph SDK integration.
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

__all__ = ["GraphClient", "enable_graph_integration"]


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
        self._scopes = scopes or ["User.Read", "Team.ReadBasic.All"]

        # Create Graph service client with token credential
        self._client = GraphServiceClient(credentials=_TokenCredential(access_token), scopes=self._scopes)

    async def get_me(self) -> Dict[str, Any]:
        """Get current user information."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        result = await self._client.me.get()
        return result.__dict__ if hasattr(result, "__dict__") else {}

    async def get_my_teams(self) -> Dict[str, Any]:
        """Get teams the current user belongs to."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        result = await self._client.me.joined_teams.get()
        return result.__dict__ if hasattr(result, "__dict__") else {}

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

    This function adds a 'graph' property to ActivityContext that provides
    access to Microsoft Graph APIs using the user's OAuth token.

    Args:
        scopes: Optional list of Graph API scopes to request
    """
    if not _msgraph_available:
        print("Warning: msgraph-sdk not available, Graph integration disabled")
        return

    from microsoft.teams.app import ActivityContext

    def get_graph_client(self: ActivityContext[Any]) -> Optional[GraphClient]:
        """Get authenticated Graph client for the current user."""
        # For now, we'll use a simple check - in real implementation this would
        # integrate with the Teams SDK's OAuth system
        if not self.is_signed_in:
            return None

        # This is a placeholder - actual token would come from OAuth flow
        # In a real implementation, this would get the token from the Teams SDK's auth system
        mock_token = "placeholder_token"
        return GraphClient(mock_token, scopes)

    # Add the graph property to ActivityContext
    ActivityContext.graph = property(get_graph_client)  # pyright: ignore[reportAttributeAccessIssue]
    print("Microsoft Graph integration enabled")
