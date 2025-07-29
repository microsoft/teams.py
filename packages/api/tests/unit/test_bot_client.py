"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
#

import pytest
from microsoft.teams.api.clients.bot import BotClient
from microsoft.teams.api.clients.bot.params import (
    GetBotSignInResourceParams,
    GetBotSignInUrlParams,
)


@pytest.mark.unit
class TestBotClient:
    """Unit tests for BotClient."""

    def test_bot_client_initialization(self, mock_http_client):
        """Test BotClient initialization."""
        client = BotClient(mock_http_client)

        assert client.http == mock_http_client
        assert client.token is not None
        assert client.sign_in is not None

    def test_bot_client_initialization_with_options(self):
        """Test BotClient initialization with ClientOptions."""
        from microsoft.teams.common.http import ClientOptions

        options = ClientOptions(base_url="https://test.api.com")
        client = BotClient(options)

        assert client.http is not None
        assert client.token is not None
        assert client.sign_in is not None

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_bot_token_get_with_client_credentials(self, mock_http_client, mock_client_credentials):
        """Test getting bot token with client credentials."""
        client = BotClient(mock_http_client)

        response = await client.token.get(mock_client_credentials)

        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in > 0

    @pytest.mark.asyncio
    async def test_bot_token_get_with_token_credentials(self, mock_http_client, mock_token_credentials):
        """Test getting bot token with token credentials."""
        client = BotClient(mock_http_client)

        response = await client.token.get(mock_token_credentials)

        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in == -1  # Token credentials return -1

    @pytest.mark.asyncio
    async def test_bot_token_get_graph_with_client_credentials(self, mock_http_client, mock_client_credentials):
        """Test getting bot graph token with client credentials."""
        client = BotClient(mock_http_client)

        response = await client.token.get_graph(mock_client_credentials)

        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in > 0

    @pytest.mark.asyncio
    async def test_bot_token_get_graph_with_token_credentials(self, mock_http_client, mock_token_credentials):
        """Test getting bot graph token with token credentials."""
        client = BotClient(mock_http_client)

        response = await client.token.get_graph(mock_token_credentials)

        assert response.token_type == "Bearer"
        assert response.access_token is not None
        assert response.expires_in == -1

    @pytest.mark.asyncio
    async def test_bot_sign_in_get_url(self, mock_http_client):
        """Test getting bot sign-in URL."""
        client = BotClient(mock_http_client)

        params = GetBotSignInUrlParams(
            state="test_state",
            code_challenge="test_challenge",
        )

        url = await client.sign_in.get_url(params)

        assert isinstance(url, str)
        assert "mock-signin.url" in url

    @pytest.mark.asyncio
    async def test_bot_sign_in_get_resource(self, mock_http_client):
        """Test getting bot sign-in resource."""
        client = BotClient(mock_http_client)

        params = GetBotSignInResourceParams(
            state="test_state",
            code_challenge="test_challenge",
        )

        response = await client.sign_in.get_resource(params)

        assert response.sign_in_link is not None
        assert response.token_exchange_resource is not None


@pytest.mark.unit
class TestBotClientHttpClientSharing:
    """Test that HTTP client is properly shared between sub-clients."""

    def test_http_client_sharing(self, mock_http_client):
        """Test that all sub-clients share the same HTTP client."""
        client = BotClient(mock_http_client)

        assert client.token.http == mock_http_client
        assert client.sign_in.http == mock_http_client

    def test_http_client_update_propagates(self, mock_http_client):
        """Test that updating HTTP client propagates to sub-clients."""
        from microsoft.teams.common.http import Client, ClientOptions

        client = BotClient(mock_http_client)
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))

        # Update the HTTP client
        client.http = new_http_client

        assert client.token.http == new_http_client
        assert client.sign_in.http == new_http_client
