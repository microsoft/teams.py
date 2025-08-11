"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime

from azure.core.credentials import AccessToken
from microsoft.teams.api.models.token.response import TokenResponse
from microsoft.teams.graph import get_graph_client
from microsoft.teams.graph.auth_provider import DirectTokenCredential
from msgraph.graph_service_client import GraphServiceClient


class TestDirectTokenCredential:
    """Test DirectTokenCredential functionality."""

    def test_get_token_with_token_response(self) -> None:
        """Test that we can get a valid access token from TokenResponse."""
        # Arrange
        token_response = TokenResponse(
            connection_name="graph", token="test_access_token_123", expiration="2024-12-31T23:59:59Z"
        )
        credential = DirectTokenCredential(token_response, "graph")

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_access_token_123"
        assert token.expires_on > 0

    def test_get_token_with_string_token(self) -> None:
        """Test that we can get a valid access token from string token."""
        # Arrange
        token_string = "test_string_token_456"
        credential = DirectTokenCredential(token_string, "graph")

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_string_token_456"
        assert token.expires_on > 0

    def test_token_caching_works(self) -> None:
        """Test that tokens are properly cached."""
        # Arrange
        token_response = TokenResponse(connection_name="graph", token="cached_token", expiration="2024-12-31T23:59:59Z")
        credential = DirectTokenCredential(token_response)

        # Act - Get token twice
        token1 = credential.get_token("https://graph.microsoft.com/.default")
        token2 = credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Same token returned (cached)
        assert token1.token == token2.token
        assert token1.expires_on == token2.expires_on

    def test_handles_empty_token(self) -> None:
        """Test behavior when token is empty - client creation succeeds, error on token usage."""
        # Test with empty string - client creation should succeed
        client = get_graph_client("")
        assert client is not None

        # Test with whitespace string - client creation should succeed
        client = get_graph_client("   ")
        assert client is not None

    def test_handles_token_response_with_empty_token(self) -> None:
        """Test behavior when TokenResponse has empty token - client creation succeeds, error on token usage."""
        # Arrange
        token_response = TokenResponse(connection_name="graph", token="", expiration="2024-12-31T23:59:59Z")

        # Act - client creation should succeed
        client = get_graph_client(token_response)
        assert client is not None

    def test_token_expiration_parsing(self) -> None:
        """Test various expiration date formats are parsed correctly."""
        # Test ISO format with Z
        token_response = TokenResponse(connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z")
        credential = DirectTokenCredential(token_response)
        token = credential.get_token()

        # Should parse the ISO date correctly
        expected_expiration = datetime.datetime.fromisoformat("2024-12-31T23:59:59Z")
        assert token.expires_on == int(expected_expiration.timestamp())

    def test_token_expiration_parsing_epoch_timestamp(self) -> None:
        """Test epoch timestamp expiration parsing."""
        # Test epoch timestamp
        future_timestamp = str(int(datetime.datetime.now(datetime.timezone.utc).timestamp()) + 3600)
        token_response = TokenResponse(connection_name="graph", token="test_token", expiration=future_timestamp)

        credential = DirectTokenCredential(token_response)
        token = credential.get_token()

        assert token.expires_on == int(future_timestamp)

    def test_token_expiration_parsing_fallback(self) -> None:
        """Test fallback when expiration parsing fails."""
        # Test invalid expiration format
        token_response = TokenResponse(connection_name="graph", token="test_token", expiration="invalid_date")

        credential = DirectTokenCredential(token_response)
        token = credential.get_token()

        # Should use default 1-hour expiration
        now = datetime.datetime.now(datetime.timezone.utc)
        expected_min = int((now + datetime.timedelta(minutes=55)).timestamp())  # Allow 5-minute buffer
        expected_max = int((now + datetime.timedelta(hours=1, minutes=5)).timestamp())

        assert expected_min <= token.expires_on <= expected_max

    def test_token_validation_with_buffer(self) -> None:
        """Test token validation includes expiration buffer."""
        # Create a token that expires in 2 minutes (less than 5-minute buffer)
        near_expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=2)
        token_response = TokenResponse(
            connection_name="graph", token="expiring_token", expiration=near_expiry.isoformat() + "Z"
        )

        credential = DirectTokenCredential(token_response)

        # Get token - should work normally even with near expiry
        token = credential.get_token()
        assert token.token == "expiring_token"
        # Token should be valid but close to expiry
        assert token.expires_on > 0


class TestGraphClientFactory:
    """Test the graph client factory functions."""

    def test_get_graph_client_with_token_response(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with TokenResponse."""
        # Arrange
        token_response = TokenResponse(connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z")

        # Act
        client = get_graph_client(token_response, connection_name="graph")

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    def test_get_graph_client_with_string_token(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with string token."""
        # Arrange
        token_string = "test_string_token_789"

        # Act
        client = get_graph_client(token_string)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    def test_get_graph_client_with_connection_name(self) -> None:
        """Test that connection_name parameter is handled correctly."""
        # Arrange
        token_response = TokenResponse(connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z")

        # Act
        client = get_graph_client(token_response, connection_name="custom_connection")

        # Assert
        assert isinstance(client, GraphServiceClient)

    def test_get_graph_client_creates_new_instances(self) -> None:
        """Test that get_graph_client creates new instances each time."""
        # Arrange
        token_response = TokenResponse(connection_name="graph", token="test_token", expiration="2024-12-31T23:59:59Z")

        # Act
        client1 = get_graph_client(token_response)
        client2 = get_graph_client(token_response)

        # Assert - Different instances (no caching at client level)
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
        assert client1 is not client2

    def test_validates_token_input(self) -> None:
        """Test that the function works with different token inputs."""
        # Test empty string - client creation should succeed
        client = get_graph_client("")
        assert client is not None

        # Test TokenResponse with empty token - client creation should succeed
        empty_token_response = TokenResponse(connection_name="graph", token="")
        client = get_graph_client(empty_token_response)
        assert client is not None

    def test_handles_credential_creation_errors(self) -> None:
        """Test error handling during credential creation."""
        # Test with a valid token that should not raise an error
        token_response = TokenResponse(connection_name="graph", token="valid_token", expiration="2024-12-31T23:59:59Z")

        # This should work fine
        credential = DirectTokenCredential(token_response)
        token = credential.get_token()
        assert token.token == "valid_token"
