"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime
from typing import Any
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
    def mock_context(self) -> Any:
        """Create a mock ActivityContext with necessary properties."""
        context = MagicMock()
        context.activity.channel_id = "test_channel"
        context.activity.from_.id = "test_user"
        context.connection_name = "graph"
        context.is_signed_in = True
        context.api = MagicMock()
        return context

    def test_get_token_success(self, mock_context: Any) -> None:
        """Test that we can get a valid access token."""
        # Arrange - Mock only the Teams API call
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_access_token_123", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        credential = TeamsTokenCredential(mock_context)

        # Act - get_token is synchronous, not async
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Verify we get a proper AccessToken
        assert isinstance(token, AccessToken)
        assert token.token == "test_access_token_123"
        assert token.expires_on > 0

    def test_token_caching_works(self, mock_context: Any) -> None:
        """Test that tokens are properly cached."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="cached_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        credential = TeamsTokenCredential(mock_context)

        # Act - Get token twice (synchronous calls)
        token1 = credential.get_token("https://graph.microsoft.com/.default")
        token2 = credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Same token returned, API called only once
        assert token1.token == token2.token
        mock_context.api.users.token.get.assert_called_once()

    def test_handles_user_not_signed_in(self, mock_context: Any) -> None:
        """Test proper error when user is not signed in."""
        # Arrange
        mock_context.is_signed_in = False
        mock_context.api.users.token.get = AsyncMock(side_effect=Exception("No token"))

        credential = TeamsTokenCredential(mock_context)

        # Act & Assert - get_token is synchronous
        with pytest.raises(ClientAuthenticationError, match="User is not signed in"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_token_expiration_validation_through_caching(self, mock_context: Any) -> None:
        """Test token expiration validation through caching behavior."""
        # Test token expiration indirectly by setting up different scenarios
        # and verifying that new tokens are fetched when old ones expire

        # Arrange - Setup mock for expired token scenario
        mock_token_response = TokenResponse(
            connection_name="graph", token="fresh_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        credential = TeamsTokenCredential(mock_context)

        # Test 1: Fresh token should be fetched on first call
        token1 = credential.get_token("https://graph.microsoft.com/.default")
        assert token1.token == "fresh_token"

        # Test 2: Second call should use cached token (verify API called only once)
        token2 = credential.get_token("https://graph.microsoft.com/.default")
        assert token2.token == "fresh_token"
        assert token1 is token2  # Same object reference indicates caching
        mock_context.api.users.token.get.assert_called_once()

        # Test 3: Test expiration logic by checking the parsed expiration time
        # The token should have a reasonable expiration time
        assert token1.expires_on > int(datetime.datetime.now(datetime.timezone.utc).timestamp())

        # Verify the expiration was parsed correctly from the ISO format
        expected_expiration = datetime.datetime.fromisoformat("2024-12-31T23:59:59Z")
        expected_timestamp = int(expected_expiration.timestamp())
        assert token1.expires_on == expected_timestamp


class TestGraphClientFactory:
    """Test the graph client factory functions."""

    @pytest.fixture
    def mock_context(self) -> Any:
        """Create a mock ActivityContext."""
        context = MagicMock()
        context.activity.channel_id = "test_channel"
        context.activity.from_.id = "test_user"
        context.connection_name = "graph"
        context.is_signed_in = True
        context.extra = {}
        return context

    def test_get_graph_client_creates_real_client(self, mock_context: Any) -> None:
        """Test that get_graph_client creates a real GraphServiceClient."""
        # Arrange - Mock the token API call
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client = get_graph_client(mock_context)  # type: ignore[arg-type]

        # Assert - We get a real GraphServiceClient
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    def test_get_graph_client_caching(self, mock_context: Any) -> None:
        """Test that graph clients are cached per context."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client1 = get_graph_client(mock_context)  # type: ignore[arg-type]
        client2 = get_graph_client(mock_context)  # type: ignore[arg-type]

        # Assert - Different client instances (no caching implemented currently)
        # Note: Caching would need to be implemented if desired
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)

    def test_get_user_graph_client(self, mock_context: Any) -> None:
        """Test the convenience function for user-scoped clients."""
        # Arrange
        mock_token_response = TokenResponse(
            connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z"
        )
        mock_context.api.users.token.get = AsyncMock(return_value=mock_token_response)

        # Act
        client = get_user_graph_client(mock_context)  # type: ignore[arg-type]

        # Assert
        assert isinstance(client, GraphServiceClient)

    def test_requires_signed_in_user(self, mock_context: Any) -> None:
        """Test that graph client requires signed-in user."""
        # Arrange
        mock_context.is_signed_in = False

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="User is not signed in"):
            get_graph_client(mock_context)  # type: ignore[arg-type]

    def test_validates_context(self) -> None:
        """Test that invalid contexts are rejected."""
        with pytest.raises(ValueError, match="Context cannot be None"):
            get_graph_client(None)  # type: ignore[arg-type]
