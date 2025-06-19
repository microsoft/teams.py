"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft.teams.api.clients.user import UserClient
from microsoft.teams.api.clients.user.params import (
    ExchangeUserTokenParams,
    GetUserAADTokenParams,
    GetUserTokenParams,
    GetUserTokenStatusParams,
    SignOutUserParams,
)
from microsoft.teams.api.models import TokenExchangeRequest


@pytest.mark.unit
@pytest.mark.asyncio
class TestUserClient:
    """Unit tests for UserClient."""

    def test_user_client_initialization(self, mock_http_client):
        """Test UserClient initialization."""
        client = UserClient(mock_http_client)

        assert client.http == mock_http_client
        assert client.token is not None

    def test_user_client_initialization_with_options(self):
        """Test UserClient initialization with ClientOptions."""
        from microsoft.teams.common.http import ClientOptions

        options = ClientOptions(base_url="https://test.api.com")
        client = UserClient(options)

        assert client.http is not None
        assert client.token is not None

    async def test_user_token_get(self, mock_http_client):
        """Test getting user token."""
        client = UserClient(mock_http_client)

        params = GetUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            code="auth_code_123",
        )

        response = await client.token.get(params)

        assert response.token is not None
        assert response.connection_name == "test_connection"

    async def test_user_token_get_aad(self, mock_http_client):
        """Test getting AAD tokens for user."""
        client = UserClient(mock_http_client)

        params = GetUserAADTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            resource_urls=["https://graph.microsoft.com", "https://api.botframework.com"],
            channel_id="test_channel_id",
        )

        response = await client.token.get_aad(params)

        assert isinstance(response, dict)
        # Mock response should return token responses for each resource

    async def test_user_token_get_status(self, mock_http_client):
        """Test getting user token status."""
        client = UserClient(mock_http_client)

        params = GetUserTokenStatusParams(
            user_id="test_user_id",
            channel_id="test_channel_id",
            include_filter="*",
        )

        response = await client.token.get_status(params)

        assert isinstance(response, list)

    async def test_user_token_sign_out(self, mock_http_client):
        """Test signing out user."""
        client = UserClient(mock_http_client)

        params = SignOutUserParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
        )

        # Should not raise an exception
        await client.token.sign_out(params)

    async def test_user_token_exchange(self, mock_http_client):
        """Test exchanging user token."""
        client = UserClient(mock_http_client)

        exchange_request = TokenExchangeRequest(
            uri="https://test.resource.com",
            token="exchange_token_123",
        )

        params = ExchangeUserTokenParams(
            user_id="test_user_id",
            connection_name="test_connection",
            channel_id="test_channel_id",
            exchange_request=exchange_request,
        )

        response = await client.token.exchange(params)

        assert response.token is not None
        assert response.connection_name == "test_connection"


@pytest.mark.unit
class TestUserClientHttpClientSharing:
    """Test that HTTP client is properly shared between sub-clients."""

    def test_http_client_sharing(self, mock_http_client):
        """Test that all sub-clients share the same HTTP client."""
        client = UserClient(mock_http_client)

        assert client.token.http == mock_http_client

    def test_http_client_update_propagates(self, mock_http_client):
        """Test that updating HTTP client propagates to sub-clients."""
        from microsoft.teams.common.http import Client, ClientOptions

        client = UserClient(mock_http_client)
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))

        # Update the HTTP client
        client.http = new_http_client

        assert client.token.http == new_http_client
