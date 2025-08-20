"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.common.http.client_token import Token
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import AuthProvider


def get_graph_client(token: Optional[Token] = None) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client using a Token.

    Args:
        token: Token data (string, StringLike, callable, or None). If None,
               will raise ClientAuthenticationError with a clear message.

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the token is None, invalid, or authentication fails

    Example:
        ```python
        # Using a string token
        graph = get_graph_client("eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs...")


        # Using a callable that returns a string
        def get_token():
            return "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs..."


        graph = get_graph_client(get_token)

        # Make Graph API calls
        me = await graph.me.get()
        messages = await graph.me.messages.get()
        ```
    """
    try:
        # Provide a clear error message for None tokens
        if token is None:
            raise ClientAuthenticationError(
                "Token cannot be None. Please provide a valid token (string, callable, or StringLike object) "
                "to authenticate with Microsoft Graph."
            )

        credential = AuthProvider(token)
        client = GraphServiceClient(credentials=credential)
        return client

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is
        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e
