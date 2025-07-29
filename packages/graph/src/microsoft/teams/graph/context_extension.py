"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from msgraph import GraphServiceClient

from .auth_provider import TeamsContextAuthProvider


class GraphIntegrationError(Exception):
    """Raised when Graph integration encounters an error."""

    def __init__(self, message: str, suggested_action: str = "") -> None:
        super().__init__(message)
        self.suggested_action = suggested_action


def enable_graph_integration() -> None:
    """Enable Graph integration for all ActivityContext instances.

    This function adds a 'graph' property to the ActivityContext class
    that provides zero-configuration access to Microsoft Graph API.

    Usage:
        from microsoft.teams.graph import enable_graph_integration

        enable_graph_integration()

        @app.on_message
        async def handler(context: ActivityContext):
            me = await context.graph.me.get()  # Just works!
    """

    @property
    def graph(self) -> GraphServiceClient:
        """Get Microsoft Graph client configured with user's token.

        Returns:
            GraphServiceClient configured with the user's authentication token

        Raises:
            GraphIntegrationError: If user is not signed in
        """
        # Lazy initialization - create client only when accessed
        if not hasattr(self, "_graph_client"):
            if not self.is_signed_in:
                raise GraphIntegrationError(
                    "User must be signed in to access Graph API.",
                    suggested_action="Call context.sign_in() first",
                )

            # Create auth provider that bridges Teams SDK -> Graph SDK
            auth_provider = TeamsContextAuthProvider(self)

            # Create Graph client with Teams SDK auth
            # Using default scope - can be customized later
            self._graph_client = GraphServiceClient(
                credentials=auth_provider,
                scopes=["https://graph.microsoft.com/.default"],
            )

        return self._graph_client

    # Add graph property to ActivityContext
    # Import here to avoid circular imports
    from microsoft.teams.app.routing import ActivityContext

    ActivityContext.graph = graph
