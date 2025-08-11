"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.common.http.client_token import Token, resolve_token
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import DirectTokenCredential


async def get_graph_client(
    token: Token,
    *,
    connection_name: Optional[str] = None,
) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client using a token.

    Args:
        token: The access token (string, callable, or other Token type)
        connection_name: OAuth connection name for logging/tracking purposes (optional)

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the token is invalid or authentication fails
        ValueError: If the token resolves to None or empty

    Example:
        ```python
        # Using string token directly
        token_string = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs..."
        graph = await get_graph_client(token_string)


        # Using token factory
        def get_token():
            return get_access_token_from_somewhere()


        graph = await get_graph_client(get_token)

        # Make Graph API calls
        me = await graph.me.get()
        messages = await graph.me.messages.get()
        ```
    """
    # Resolve the token to a string
    resolved_token = await resolve_token(token)

    if not resolved_token:
        raise ValueError("Token resolved to None or empty")

    try:
        credential = DirectTokenCredential(resolved_token, connection_name=connection_name)

        client = GraphServiceClient(credentials=credential)

        return client

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is

        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e


__all__ = [
    "get_graph_client",
]
