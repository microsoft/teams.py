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
    """Unit tests for DirectTokenCredential functionality."""

    def test_get_token_with_callable(self) -> None:
        """Test that we can get a valid access token from callable that returns TokenProtocol."""

        # Arrange
        def get_token():
            return _TokenData("test_access_token_123")

        credential = DirectTokenCredential(get_token)

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
        def get_token():
            return _TokenData("cached_token_456")

        credential = DirectTokenCredential(get_token)

        # Act - Get token twice
        token1 = credential.get_token("https://graph.microsoft.com/.default")
        token2 = credential.get_token("https://graph.microsoft.com/.default")

        # Assert - Same token returned (cached)
        assert token1.token == token2.token
        assert token1.expires_on == token2.expires_on

    def test_handles_empty_token_in_credential(self) -> None:
        """Test behavior when token callable returns empty data - should raise appropriate errors."""
        from azure.core.exceptions import ClientAuthenticationError

        # Test with empty token - should raise error when getting token
        def get_empty_token():
            return _TokenData("")

        credential = DirectTokenCredential(get_empty_token)
        with pytest.raises(ClientAuthenticationError, match="Token data is missing access_token"):
            credential.get_token("https://graph.microsoft.com/.default")

        # Test with whitespace string - should work (whitespace is considered valid)
        def get_whitespace_token():
            return _TokenData("   ")

        credential = DirectTokenCredential(get_whitespace_token)
        token = credential.get_token("https://graph.microsoft.com/.default")
        assert token.token == "   "


class TestGraphClientFactory:
    """Unit tests for the graph client factory functions."""

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
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_graph_client_with_connection_name(self) -> None:
        """Test that connection_name parameter is handled correctly."""

        # Arrange
        def get_token():
            return _TokenData("test_token_with_connection")

        # Act
        client = await get_graph_client(get_token, connection_name="custom_connection")

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_get_graph_client_creates_new_instances(self) -> None:
        """Test that get_graph_client creates new instances each time."""

        # Arrange
        def get_token():
            return _TokenData("test_token_instances")

        # Act
        client1 = await get_graph_client(get_token)
        client2 = await get_graph_client(get_token)

        # Assert - Different instances (no caching at client level)
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
        assert client1 is not client2

    @pytest.mark.asyncio
    async def test_handles_credential_creation_errors(self) -> None:
        """Test error handling during credential creation."""

        # Test with a valid token callable that should not raise an error
        def get_token():
            return _TokenData("valid_token_test")

        # This should work fine
        credential = DirectTokenCredential(get_token)
        token = credential.get_token()
        assert token.token == "valid_token_test"

        # Creating client should also work with callable
        client = await get_graph_client(get_token)
        assert isinstance(client, GraphServiceClient)
