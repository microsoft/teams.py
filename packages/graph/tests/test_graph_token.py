"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime

import pytest
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.graph import get_graph_client
from microsoft.teams.graph.auth_provider import DirectTokenCredential
from msgraph.graph_service_client import GraphServiceClient


class TestDirectTokenCredential:
    """Test DirectTokenCredential functionality with various Token types."""

    def test_get_token_with_string(self) -> None:
        """Test that we can get a valid access token from a string token."""

        # Arrange
        token_str = "test_access_token_123"
        credential = DirectTokenCredential(token_str, "graph")

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

    def test_get_token_with_callable(self) -> None:
        """Test that we can get a valid access token from a callable returning a string."""

        # Arrange
        def get_token():
            return "test_callable_token_456"

        credential = DirectTokenCredential(get_token, "graph")

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_callable_token_456"

    @pytest.mark.asyncio
    async def test_get_token_with_async_callable(self) -> None:
        """Test that we can get a valid access token from an async callable."""

        # Arrange
        async def get_token_async():
            return "test_async_token_789"

        credential = DirectTokenCredential(get_token_async, "graph")

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_async_token_789"

    def test_get_token_with_failing_callable(self) -> None:
        """Test that failing callable raises appropriate error."""

        # Arrange
        def failing_callable():
            raise ValueError("Simulated token retrieval failure")

        credential = DirectTokenCredential(failing_callable, "graph")

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Failed to resolve token"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_none_token(self) -> None:
        """Test that None token raises appropriate error."""

        # Arrange
        credential = DirectTokenCredential(None, "graph")

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token resolved to None or empty string"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_empty_string(self) -> None:
        """Test that empty string token raises appropriate error."""

        # Arrange
        credential = DirectTokenCredential("", "graph")

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token resolved to None or empty string"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_whitespace_only(self) -> None:
        """Test that whitespace-only token raises appropriate error."""

        # Arrange
        credential = DirectTokenCredential("   \t\n  ", "graph")

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token contains only whitespace"):
            credential.get_token("https://graph.microsoft.com/.default")


class TestGraphClientFactory:
    """Test get_graph_client factory function."""

    @pytest.mark.asyncio
    async def test_get_graph_client_with_string_token(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with string token."""

        # Arrange
        token = "test_string_token_123"

        # Act
        client = await get_graph_client(token)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_graph_client_with_callable(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with callable token."""

        # Arrange
        def get_token():
            return "test_token_callable_789"

        # Act
        client = await get_graph_client(get_token)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    @pytest.mark.asyncio
    async def test_get_graph_client_with_connection_name(self) -> None:
        """Test that connection_name parameter is handled correctly."""

        # Arrange
        token = "test_token_with_connection"

        # Act
        client = await get_graph_client(token, connection_name="custom_connection")

        # Assert
        assert isinstance(client, GraphServiceClient)

    @pytest.mark.asyncio
    async def test_get_graph_client_creates_new_instances(self) -> None:
        """Test that get_graph_client creates new instances each time."""

        # Arrange
        token = "test_token_instances"

        # Act
        client1 = await get_graph_client(token)
        client2 = await get_graph_client(token)

        # Assert - Different instances (no caching at client level)
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
        assert client1 is not client2
