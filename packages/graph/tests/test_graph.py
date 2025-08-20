"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import datetime

import pytest
from azure.core.credentials import AccessToken
from azure.core.exceptions import ClientAuthenticationError
from microsoft.teams.graph import get_graph_client
from microsoft.teams.graph.auth_provider import AuthProvider
from msgraph.graph_service_client import GraphServiceClient


class TestAuthProvider:
    """Unit tests for AuthProvider functionality."""

    def test_get_token_with_string(self) -> None:
        """Test that we can get a valid access token from a string token."""

        # Arrange
        token_str = "test_access_token_123"
        credential = AuthProvider(token_str)

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

    def test_get_token_with_string_basic(self) -> None:
        """Test that we can get a valid access token from a string token."""

        # Arrange
        token_str = "test_access_token_basic"
        credential = AuthProvider(token_str)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_access_token_basic"

    def test_get_token_with_callable(self) -> None:
        """Test that we can get a valid access token from a callable that returns a string."""

        # Arrange
        def get_token():
            return "test_callable_token_456"

        credential = AuthProvider(get_token)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_callable_token_456"

    def test_get_token_with_callable_basic(self) -> None:
        """Test that we can get a valid access token from a callable."""

        # Arrange
        def get_token():
            return "test_callable_token_basic"

        credential = AuthProvider(get_token)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_callable_token_basic"

    def test_get_token_with_jwt_extracts_expiration(self) -> None:
        """Test that JWT tokens have their expiration extracted correctly."""
        import time

        import jwt

        # Arrange - Create a valid JWT token with specific expiration
        exp_time = int(time.time()) + 3600  # 1 hour from now
        payload = {"exp": exp_time, "aud": "test"}
        jwt_token = jwt.encode(payload, "secret", algorithm="HS256")

        credential = AuthProvider(jwt_token)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.expires_on == exp_time  # Should use JWT expiration, not default

    def test_get_token_with_non_jwt_uses_default_expiration(self) -> None:
        """Test that non-JWT tokens use default 1-hour expiration."""
        import time

        # Arrange
        token_str = "not_a_jwt_token_123"
        credential = AuthProvider(token_str)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "not_a_jwt_token_123"
        # Should use default expiration (approximately 1 hour from now)
        now = int(time.time())
        assert abs(token.expires_on - (now + 3600)) < 60  # Within 1 minute tolerance

    @pytest.mark.asyncio
    async def test_get_token_with_async_callable(self) -> None:
        """Test that we can get a valid access token from an async callable."""

        # Arrange
        async def get_token_async():
            return "test_async_token_789"

        credential = AuthProvider(get_token_async)

        # Act
        token = credential.get_token("https://graph.microsoft.com/.default")

        # Assert
        assert isinstance(token, AccessToken)
        assert token.token == "test_async_token_789"

    def test_get_token_with_none(self) -> None:
        """Test that None token raises appropriate error."""

        # Arrange
        credential = AuthProvider(None)

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token resolved to None or empty string"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_empty_string(self) -> None:
        """Test that empty string token raises appropriate error."""

        # Arrange
        credential = AuthProvider("")

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token resolved to None or empty string"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_whitespace_only(self) -> None:
        """Test that whitespace-only token raises appropriate error."""

        # Arrange
        credential = AuthProvider("   \t\n  ")

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token contains only whitespace"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_callable_returning_none(self) -> None:
        """Test that callable returning None raises appropriate error."""

        # Arrange
        def get_token():
            return None

        credential = AuthProvider(get_token)

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Token resolved to None or empty string"):
            credential.get_token("https://graph.microsoft.com/.default")

    def test_get_token_with_failing_callable(self) -> None:
        """Test that failing callable raises appropriate error."""

        # Arrange
        def failing_callable():
            raise ValueError("Simulated token retrieval failure")

        credential = AuthProvider(failing_callable)

        # Act & Assert
        with pytest.raises(ClientAuthenticationError, match="Failed to resolve token"):
            credential.get_token("https://graph.microsoft.com/.default")


class TestGraphClientFactory:
    """Unit tests for the graph client factory functions."""

    def test_get_graph_client_with_string_token(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with string token."""

        # Arrange
        token = "test_string_token_123"

        # Act
        client = get_graph_client(token)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    def test_get_graph_client_with_callable(self) -> None:
        """Test that get_graph_client creates a real GraphServiceClient with callable token."""

        # Arrange
        def get_token():
            return "test_token_callable_789"

        # Act
        client = get_graph_client(get_token)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    def test_get_graph_client_with_async_callable(self) -> None:
        """Test that get_graph_client works with async callable token."""

        # Arrange
        async def get_token_async():
            return "test_async_token_456"

        # Act
        client = get_graph_client(get_token_async)

        # Assert
        assert isinstance(client, GraphServiceClient)
        assert client is not None

    def test_get_graph_client_basic(self) -> None:
        """Test that get_graph_client works with basic parameters."""

        # Arrange
        token = "test_token_basic"

        # Act
        client = get_graph_client(token)

        # Assert
        assert isinstance(client, GraphServiceClient)

    def test_get_graph_client_creates_new_instances(self) -> None:
        """Test that get_graph_client creates new instances each time."""

        # Arrange
        token = "test_token_instances"

        # Act
        client1 = get_graph_client(token)
        client2 = get_graph_client(token)

        # Assert - Different instances (no caching at client level)
        assert isinstance(client1, GraphServiceClient)
        assert isinstance(client2, GraphServiceClient)
        assert client1 is not client2

    def test_get_graph_client_with_none_token(self) -> None:
        """Test that None token raises appropriate error immediately."""
        from azure.core.exceptions import ClientAuthenticationError

        # Act & Assert - should raise ClientAuthenticationError immediately
        with pytest.raises(ClientAuthenticationError) as exc_info:
            get_graph_client(None)

        # Verify the error message is clear and helpful
        assert "Token cannot be None" in str(exc_info.value)
        assert "Please provide a valid token" in str(exc_info.value)

    def test_get_graph_client_with_failing_callable(self) -> None:
        """Test error handling when token callable fails."""

        # Arrange
        def failing_token():
            raise RuntimeError("Simulated token failure")

        # Act - client creation should succeed
        client = get_graph_client(failing_token)
        assert client is not None

        # But using the credential should fail
        from microsoft.teams.graph.auth_provider import AuthProvider

        credential = AuthProvider(failing_token)
        with pytest.raises(ClientAuthenticationError):
            credential.get_token("https://graph.microsoft.com/.default")
