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
        # Use scopes that are actually granted in your Azure App Registration
        self._scopes = scopes or ["User.Read", "User.ReadBasic.All", "Team.ReadBasic.All", "offline_access"]
        print(f"These are the scopes requested: {scopes}")
        print(f"These are the default scopes: {self._scopes}")

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
            print("✓ Token has User.Read scope - /me call succeeded")
        except Exception as e:
            print(f"✗ Token missing User.Read scope - /me call failed: {e}")

    async def get_my_teams(self) -> Dict[str, Any]:
        """Get teams the current user belongs to."""
        if not self._client:
            raise RuntimeError("Graph client not initialized")
        print(f"These are the scopes in the request: {self._scopes}")
        try:
            result = await self._client.me.joined_teams.get()
            return result.__dict__ if hasattr(result, "__dict__") else {}
        except Exception as e:
            print(f"Error getting teams: {e}")
            # Check if it's a permission error
            if "403" in str(e) or "Forbidden" in str(e):
                print("\n🚨 PERMISSIONS ERROR:")
                print("Your OAuth token doesn't have the required Graph API permissions.")
                print("\nCURRENT AZURE PERMISSIONS STATUS:")
                print("✅ User.Read (Delegated) - Granted")
                print("✅ User.ReadBasic.All (Delegated) - Granted")
                print("✅ Team.ReadBasic.All (Delegated) - Granted")
                print("✅ offline_access (Delegated) - Granted")
                print("⚠️  User.Read.All (Delegated) - NOT GRANTED")
                print("⚠️  Team.ReadBasic.All (Application) - NOT GRANTED")
                print("\nTO FIX THIS:")
                print("1. In Azure Portal, click 'Grant admin consent for teamsaiacc' button")
                print("2. Or remove the Application permission for Team.ReadBasic.All (you only need Delegated)")
                print("3. Update your Teams app OAuth connection to request these scopes:")
                print("   User.Read User.ReadBasic.All Team.ReadBasic.All offline_access")
                print("4. Users need to sign in again to get new permissions")
                print(f"Required scopes: {self._scopes}")
            raise

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
        print("Warning: msgraph-sdk not available, Graph integration disabled")
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
    print("Microsoft Graph integration enabled")
