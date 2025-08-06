"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Optional

from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.app.routing.activity_context import ActivityContext
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import TeamsTokenCredential

# Default Microsoft Graph scopes
_DEFAULT_SCOPES = ["https://graph.microsoft.com/.default"]


async def get_graph_client(
    context: "ActivityContext[Any]",
    scopes: Optional[List[str]] = None,
    connection_name: Optional[str] = None,
) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client for the authenticated user.

    This function creates a GraphServiceClient instance that uses the Teams OAuth token
    from the provided context.

    Args:
        context: The Teams activity context containing user authentication state
        scopes: List of Microsoft Graph scopes (defaults to ['.default'])
        connection_name: OAuth connection name (defaults to context.connection_name)

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the user is not signed in or authentication fails
        ValueError: If the context is invalid

    Example:
        ```python
        @app.on_message
        async def handle_message(ctx: ActivityContext):
            if not ctx.is_signed_in:
                await ctx.sign_in()
                return

            # Get Graph client with default scopes
            graph = await get_graph_client(ctx)

            # Make Graph API calls
            me = await graph.me.get()
            messages = await graph.me.messages.get()

            await ctx.send(f"Hello {me.display_name}, you have {len(messages.value)} messages")
        ```

        ```python
        # Custom scopes example
        graph = await get_graph_client(ctx, scopes=["User.Read", "Mail.Read"])
        ```
    """
    if not context:
        raise ValueError("Context cannot be None")

    if not context.activity or not context.activity.from_:
        raise ValueError("Context must contain valid activity with sender information")

    # Use provided scopes or defaults
    request_scopes = scopes or _DEFAULT_SCOPES
    connection = connection_name or context.connection_name

    # Verify user is signed in
    if not context.is_signed_in:
        raise ClientAuthenticationError(
            "User is not signed in. Call 'await context.sign_in()' before accessing Microsoft Graph."
        )

    try:
        # Create Teams token credential
        credential = TeamsTokenCredential(context, connection)

        # Create Graph service client
        client = GraphServiceClient(credentials=credential, scopes=request_scopes)

        return client

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is

        # Wrap other exceptions with context
        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e


async def get_user_graph_client(context: "ActivityContext[Any]") -> GraphServiceClient:
    """
    Convenience function to get a Graph client with user-focused scopes.

    This is equivalent to calling get_graph_client() with User.Read scope,
    but provides a more explicit name for user-focused operations.

    Args:
        context: The Teams activity context containing user authentication state

    Returns:
        GraphServiceClient: A configured client for user-focused Graph operations

    Raises:
        ClientAuthenticationError: If the user is not signed in or authentication fails
    """
    return await get_graph_client(context, scopes=["User.Read"])


# Export public API
__all__ = [
    "get_graph_client",
    "get_user_graph_client",
    "TeamsTokenCredential",
]
