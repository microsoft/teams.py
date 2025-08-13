"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Callable, Optional

from azure.core.exceptions import ClientAuthenticationError
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import DirectTokenCredential
from .protocols import TokenProtocol


async def get_graph_client(
    token_callable: Callable[[], TokenProtocol],
    *,
    connection_name: Optional[str] = None,
) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client using a TokenProtocol callable.

    Args:
        token_callable: A callable that returns token data implementing TokenProtocol
        connection_name: OAuth connection name for logging/tracking purposes (optional)

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the token is invalid or authentication fails

    Example:
        ```python
        def get_token():
            class TokenData:
                access_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIs..."
                expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)
                token_type = "Bearer"
                scope = "https://graph.microsoft.com/.default"

            return TokenData()


        graph = await get_graph_client(get_token)

        # Make Graph API calls
        me = await graph.me.get()
        messages = await graph.me.messages.get()
        ```
    """
    try:
        credential = DirectTokenCredential(token_callable, connection_name=connection_name)
        client = GraphServiceClient(credentials=credential)
        return client

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is
        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e


__all__ = [
    "get_graph_client",
]
