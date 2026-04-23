"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from azure.core.exceptions import ClientAuthenticationError
from kiota_authentication_azure.azure_identity_authentication_provider import (
    AzureIdentityAuthenticationProvider,
)
from microsoft_teams.common.http.client_token import Token
from msgraph.graph_request_adapter import GraphRequestAdapter
from msgraph.graph_service_client import GraphServiceClient

from .auth_provider import AuthProvider


def get_graph_client(
    token: Optional[Token] = None,
    base_url: Optional[str] = None,
) -> GraphServiceClient:
    """
    Get a configured Microsoft Graph client using a Token.

    Args:
        token: Token data (string, StringLike, callable, or None). If None,
               will raise ClientAuthenticationError with a clear message.
        base_url: Optional Graph API base URL override for sovereign clouds
               (e.g. "https://graph.microsoft.us" for GCCH). When provided,
               the client routes HTTP calls to this endpoint + "/v1.0/". When
               None, the public Graph endpoint is used.

    Returns:
        GraphServiceClient: A configured client ready for Microsoft Graph API calls

    Raises:
        ClientAuthenticationError: If the token is None, invalid, or authentication fails

    Example:
        ```python
        # Public cloud (default)
        graph = get_graph_client("eyJ0eXAiOiJKV1Qi...")

        # Sovereign cloud (GCCH)
        graph = get_graph_client(token, base_url="https://graph.microsoft.us")
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

        if base_url is None:
            return GraphServiceClient(credentials=credential)

        # Build a custom request adapter with the sovereign base URL.
        # Normalize: strip any trailing slash on caller's input, then append "/v1.0/"
        # to match the msgraph-sdk default shape ("https://graph.microsoft.com/v1.0/").
        auth_provider = AzureIdentityAuthenticationProvider(credential)
        adapter = GraphRequestAdapter(auth_provider)
        adapter.base_url = f"{base_url.rstrip('/')}/v1.0/"
        return GraphServiceClient(request_adapter=adapter)

    except Exception as e:
        if isinstance(e, ClientAuthenticationError):
            raise  # Re-raise authentication errors as-is
        raise ClientAuthenticationError(f"Failed to create Microsoft Graph client: {str(e)}") from e
