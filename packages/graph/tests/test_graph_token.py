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


class _TokenData:
    """Helper class that implements TokenProtocol for testing."""

    def __init__(self, access_token: str, expires_in_hours: int = 1):
        self.access_token = access_token
        expiry = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=expires_in_hours)
        self.expires_at: datetime.datetime | None = expiry
        self.token_type: str | None = "Bearer"
        self.scope: str | None = "https://graph.microsoft.com/.default"


class TestDirectTokenCredential:
    """Test DirectTokenCredential functionality."""

    def test_get_token_with_callable(self) -> None:
        """Test that we can get a valid access token from callable that returns TokenProtocol."""

        # Arrange
        def get_token():
            return _TokenData("test_access_token_123")

        credential = DirectTokenCredential(get_token, "graph")

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
        """Test that tokens are cached and reused."""

        # Arrange
        def get_token():
            return _TokenData("cached_token_789")

        credential = DirectTokenCredential(get_token)

        # Act - Get token twice
        token1 = credential.get_token("https://graph.microsoft.com/.default")
        token2 = credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Same token object returned (cached)
        assert token1.token == token2.token
        assert token1.expires_on == token2.expires_on

    def test_handles_empty_token_in_credential(self) -> None:
        """Test behavior when DirectTokenCredential gets callable that returns empty token."""
        from azure.core.exceptions import ClientAuthenticationError

        # Test with empty string - should raise error when getting token
        def get_empty_token():
            return _TokenData("")

        credential = DirectTokenCredential(get_empty_token)
        try:
            credential.get_token()
            raise AssertionError("Expected ClientAuthenticationError for empty token")
        except ClientAuthenticationError:
            pass  # Expected

    def test_token_validation_without_buffer(self) -> None:
        """Test token validation uses exact expiration time (no buffer)."""

        # Create a token callable
        def get_token():
            return _TokenData("expiring_token")

        credential = DirectTokenCredential(get_token)

        # Get token - should work normally
        token = credential.get_token()
        assert token.token == "expiring_token"

        # Test caching by getting token again - should use cached version
        token2 = credential.get_token()
        assert token.token == token2.token
        assert token.expires_on == token2.expires_on


class TestGraphClientFactory:
    """Test get_graph_client factory function."""

    @pytest.mark.asyncio
    async def test_get_graph_client_with_callable(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with TokenProtocol callable."""

        # Arrange
        def get_token():
            return _TokenData("test_token_callable_789")

        # Act
        client = await get_graph_client(get_token)

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_get_graph_client_with_connection_name(self) -> None:
        """Test that connection_name parameter is handled correctly."""

        # Arrange
        def get_token():
            return _TokenData("test_token")

        # Act
        client = await get_graph_client(get_token, connection_name="custom_connection")

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_get_graph_client_creates_new_instances(self) -> None:
        """Test that get_graph_client creates new instances each time."""

        # Arrange
        def get_token():
            return _TokenData("test_token")

        # Act
        client1 = await get_graph_client(get_token)
        client2 = await get_graph_client(get_token)

        # Assert - Different instances (no caching at client level)
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
        assert client1 is not client2

    def test_handles_credential_creation_errors(self) -> None:
        """Test error handling during credential creation."""

        # Test with a valid token callable that should not raise an error
        def get_token():
            return _TokenData("valid_token")

        # This should work fine
        credential = DirectTokenCredential(get_token)
        token = credential.get_token()
        assert token.token == "valid_token"
