"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime

import pytest
from azure.core.credentials import AccessToken
from microsoft.teams.graph import get_graph_client
from microsoft.teams.graph.auth_provider import DirectTokenCredential
from msgraph.graph_service_client import GraphServiceClient


class TestDirectTokenCredential:
    """Unit tests for DirectTokenCredential functionality."""

    def test_get_token_with_string_token(self) -> None:
        """Test that we can get a valid access token from string token."""
        # Arrange
        token_string = "test_access_token_123"
        credential = DirectTokenCredential(token_string)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_access_token_123"
        # Token should expire in ~1 hour (with some tolerance)
        now = datetime.datetime.now(datetime.timezone.utc)
        expected_expiry = now + datetime.timedelta(hours=1)
        actual_expiry = datetime.datetime.fromtimestamp(token.expires_on, tz=datetime.timezone.utc)
        time_diff = abs((actual_expiry - expected_expiry).total_seconds())
        assert time_diff < 60  # Should be within 1 minute

    def test_token_caching_works(self) -> None:
        """Test that tokens are properly cached."""
        # Arrange
        token_string = "cached_token_456"
        credential = DirectTokenCredential(token_string)

        # Act - Get token twice
        token1 = credential.get_token("https://graph.microsoft.com/.default")
        token2 = credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Same token returned (cached)
        assert token1.token == token2.token
        assert token1.expires_on == token2.expires_on

    def test_handles_empty_token_in_credential(self) -> None:
        """Test behavior when token is empty in credential - should raise appropriate errors."""
        from azure.core.exceptions import ClientAuthenticationError

        # Test with empty string - should raise error when getting token
        credential = DirectTokenCredential("")
        with pytest.raises(ClientAuthenticationError, match="Token string is empty or None"):
            credential.get_token("https://graph.microsoft.com/.default")

        # Test with whitespace string - should work (whitespace is considered valid)
        credential = DirectTokenCredential("   ")
        token = credential.get_token("https://graph.microsoft.com/.default")
        assert token.token == "   "


class TestGraphClientFactory:
    """Unit tests for the graph client factory functions."""

    @pytest.mark.asyncio
    async def test_get_graph_client_with_string_token(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with string token."""
        # Arrange
        token_string = "test_string_token_789"

        # Act
        client = await get_graph_client(token_string)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_graph_client_with_connection_name(self) -> None:
        """Test that connection_name parameter is handled correctly."""
        # Arrange
        token_string = "test_token_with_connection"

        # Act
        client = await get_graph_client(token_string, connection_name="custom_connection")

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_get_graph_client_creates_new_instances(self) -> None:
        """Test that get_graph_client creates new instances each time."""
        # Arrange
        token_string = "test_token_instances"

        # Act
        client1 = await get_graph_client(token_string)
        client2 = await get_graph_client(token_string)

        # Assert - Different instances (no caching at client level)
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
        assert client1 is not client2

    @pytest.mark.asyncio
    async def test_validates_token_input(self) -> None:
        """Test that the function properly validates token inputs."""
        # Test empty string - should raise ValueError
        with pytest.raises(ValueError, match="Token resolved to None or empty"):
            await get_graph_client("")

        # Test valid token - should work
        client = await get_graph_client("valid_token")
        assert client is not None

    @pytest.mark.asyncio
    async def test_handles_credential_creation_errors(self) -> None:
        """Test error handling during credential creation."""
        # Test with a valid token that should not raise an error
        token_string = "valid_token_test"

        # This should work fine
        credential = DirectTokenCredential(token_string)
        token = credential.get_token()
        assert token.token == "valid_token_test"

        # Creating client should also work
        client = await get_graph_client(token_string)
        assert isinstance(client, GraphServiceClient)
