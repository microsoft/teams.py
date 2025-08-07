"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.app.routing.activity_context import ActivityContext
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import TeamsTokenCredential

# Remove default scopes - let Graph SDK handle defaults


def get_graph_client(
    context: "ActivityContext[Any]",
    connection_name: Optional[str] = None,
) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client for the authenticated user.

    This function creates a GraphServiceClient instance that uses the Teams OAuth token
    from the provided context.

    Args:
        context: The Teams activity context containing user authentication state
        connection_name: OAuth connection name (defaults to context.connection_name)

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the user is not signed in or authentication fails
        ValueError: If the context is invalid

    Example:
        ```python
        @app.on_message
        def handle_message(ctx: ActivityContext):
            if not ctx.is_signed_in:
                # User needs to sign in first
                return

            # Get Graph client (now synchronous)
            graph = get_graph_client(ctx)

            # Make Graph API calls
            me = graph.me.get()
            messages = graph.me.messages.get()

            ctx.send(f"Hello {me.display_name}, you have {len(messages.value)} messages")
        ```
    """
    if not context:
        raise ValueError("Context cannot be None")

    if not context.activity or not context.activity.from_:
        raise ValueError("Context must contain valid activity with sender information")

    connection = connection_name or context.connection_name

    # Verify user is signed in
    if not context.is_signed_in:
        raise ClientAuthenticationError(
            "User is not signed in. Call 'context.sign_in()' before accessing Microsoft Graph."
        )

    try:
        # Create Teams token credential
        credential = TeamsTokenCredential(context, connection)

        # Create Graph service client (let SDK handle default scopes)
        client = GraphServiceClient(credentials=credential)

        return client

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is

        # Wrap other exceptions with context
        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e


def get_user_graph_client(context: "ActivityContext[Any]") -> GraphServiceClient:
    """
    Convenience function to get a Graph client for user-focused operations.

    This is equivalent to calling get_graph_client() but provides a more explicit name
    for user-focused operations.

    Args:
        context: The Teams activity context containing user authentication state

    Returns:
        GraphServiceClient: A configured client for user-focused Graph operations

    Raises:
        ClientAuthenticationError: If the user is not signed in or authentication fails
    """
    return get_graph_client(context)


# Export public API
__all__ = [
    "get_graph_client",
    "get_user_graph_client",
    "TeamsTokenCredential",
]
