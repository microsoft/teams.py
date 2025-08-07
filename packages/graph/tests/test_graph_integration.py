"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Tests for Microsoft Teams Graph Integration.
"""

import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.api.models.token.response import TokenResponse
from microsoft.teams.graph import get_graph_client, get_user_graph_client
from microsoft.teams.graph.auth_provider import TeamsTokenCredential
from msgraph.graph_service_client import GraphServiceClient


class TestTeamsTokenCredential:
    """Test TeamsTokenCredential functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ActivityContext with necessary properties."""
        context = MagicMock()
        context.activity.channel_id = "test_channel"
        context.activity.from_.id = "test_user"
        context.connection_name = "graph"
        context.is_signed_in = True
        context.api = MagicMock()
        return context

    @pytest.mark.asyncio
    async def test_get_token_success(self, mock_context):
        """Test that we can get a valid access token."""
        # Arrange - Mock only the Teams API call
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_access_token_123", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        credential = TeamsTokenCredential(mock_context)

        # Act
        token = await credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Verify we get a proper AccessToken
        assert isinstance(token, AccessToken)
        assert token.token == "test_access_token_123"
        assert token.expires_on > 0

    @pytest.mark.asyncio
    async def test_token_caching_works(self, mock_context):
        """Test that tokens are properly cached."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="cached_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        credential = TeamsTokenCredential(mock_context)

        # Act - Get token twice
        token1 = await credential.get_token("https://graph.microsoft.com/.default")
        token2 = await credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Same token returned, API called only once
        assert token1.token == token2.token
        mock_context.api.users.token.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_user_not_signed_in(self, mock_context):
        """Test proper error when user is not signed in."""
        # Arrange
        mock_context.is_signed_in = False
        mock_context.api.users.token.get = AsyncMock(side_effect=Exception("No token"))

        credential = TeamsTokenCredential(mock_context)

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="User is not signed in"):
            await credential.get_token("https://graph.microsoft.com/.default")

    def test_token_expiration_validation(self, mock_context):
        """Test token expiration validation logic."""
        credential = TeamsTokenCredential(mock_context)

        # Test valid token (expires in 1 hour)
        future_time = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=1)).timestamp())
        valid_token = AccessToken("token", future_time)
        assert credential._is_token_valid(valid_token) is True

        # Test expired token
        past_time = int((datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)).timestamp())
        expired_token = AccessToken("token", past_time)
        assert credential._is_token_valid(expired_token) is False

        # Test token expiring soon (within 5-minute buffer)
        soon_time = int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=2)).timestamp())
        soon_token = AccessToken("token", soon_time)
        assert credential._is_token_valid(soon_token) is False


class TestGraphClientFactory:
    """Test the graph client factory functions."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock ActivityContext."""
        context = MagicMock()
        context.activity.channel_id = "test_channel"
        context.activity.from_.id = "test_user"
        context.connection_name = "graph"
        context.is_signed_in = True
        context.extra = {}
        return context

    @pytest.mark.asyncio
    async def test_get_graph_client_creates_real_client(self, mock_context):
        """Test that get_graph_client creates a real GraphServiceClient."""
        # Arrange - Mock the token API call
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client = await get_graph_client(mock_context)

        # Assert - We get a real GraphServiceClient
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_graph_client_with_custom_scopes(self, mock_context):
        """Test get_graph_client with custom scopes."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client = await get_graph_client(mock_context, scopes=["User.Read", "Mail.Read"])

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_get_graph_client_caching(self, mock_context):
        """Test that graph clients are cached per context."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client1 = await get_graph_client(mock_context)
        client2 = await get_graph_client(mock_context)

        # Assert - Same client instance returned
        assert client1 is client2

    @pytest.mark.asyncio
    async def test_get_user_graph_client(self, mock_context):
        """Test the convenience function for user-scoped clients."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client = await get_user_graph_client(mock_context)

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_requires_signed_in_user(self, mock_context):
        """Test that graph client requires signed-in user."""
        # Arrange
        mock_context.is_signed_in = False

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="User is not signed in"):
            await get_graph_client(mock_context)

    @pytest.mark.asyncio
    async def test_validates_context(self):
        """Test that invalid contexts are rejected."""
        with pytest.raises(ValueError, match="Context cannot be None"):
            await get_graph_client(None)

    @pytest.mark.asyncio
    async def test_different_scopes_create_different_clients(self, mock_context):
        """Test that different scopes create separate cached clients."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client1 = await get_graph_client(mock_context, scopes=["User.Read"])
        client2 = await get_graph_client(mock_context, scopes=["Mail.Read"])

        # Assert - Different clients for different scopes
        assert client1 is not client2
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
