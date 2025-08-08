"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.api.models.token.response import TokenResponse
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import DirectTokenCredential


def get_graph_client(
    token: Union[str, TokenResponse],
    *,
    connection_name: Optional[str] = None,
) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client using a direct token.

    Args:
        token: The access token (string) or TokenResponse object containing the token
        connection_name: OAuth connection name for logging/tracking purposes (optional)

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the token is invalid or authentication fails
        ValueError: If the token is None or empty

    Example:
        ```python
        # Using TokenResponse (recommended - includes expiration info)
        token_params = GetUserTokenParams(
            channel_id=ctx.activity.channel_id,
            user_id=ctx.activity.from_.id,
            connection_name=ctx.connection_name,
        )
        token_response = await ctx.api.users.token.get(token_params)
        graph = get_graph_client(token_response, connection_name="graph")

        # Using string token directly
        token_string = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs..."
        graph = get_graph_client(token_string)

        # Make Graph API calls
        me = await graph.me.get()
        messages = await graph.me.messages.get()
        ```
    """
    if not token:
        raise ValueError("Token cannot be None or empty")

    if isinstance(token, TokenResponse) and not token.token:
        raise ValueError("TokenResponse must contain a valid token")

    if isinstance(token, str) and not token.strip():
        raise ValueError("Token string cannot be empty or whitespace")

    try:
        # Create direct token credential
        credential = DirectTokenCredential(token, connection_name)

        # Create Graph service client
        client = GraphServiceClient(credentials=credential)

        return client

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is

        # Wrap other exceptions with context
        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e


# Export public API
__all__ = [
    "get_graph_client",
    "DirectTokenCredential",
]
