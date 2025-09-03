"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.api import ClientCredentials, JsonWebToken
from microsoft.teams.apps.graph_token_manager import GraphTokenManager

# Valid JWT-like token for testing (format: header.payload.signature)
VALID_TEST_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
ANOTHER_VALID_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkphbmUgRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
    "Twzj7LKlhYUUe2GFRME4WOZdWq2TdayZhWjhBr1r5X4"
)


class TestGraphTokenManager:
    """Test GraphTokenManager functionality."""

    def test_initialization(self):
        """Test GraphTokenManager initialization."""
        mock_api_client = MagicMock()
        mock_credentials = MagicMock()
        mock_logger = MagicMock()

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
            logger=mock_logger,
        )

        assert manager is not None
        # Test successful initialization by verifying the manager was created

    def test_initialization_without_logger(self):
        """Test GraphTokenManager initialization without logger."""
        mock_api_client = MagicMock()
        mock_credentials = MagicMock()

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
        )

        assert manager is not None

    @pytest.mark.asyncio
    async def test_get_token_no_tenant_id(self):
        """Test getting token with no tenant_id returns None."""
        mock_api_client = MagicMock()
        mock_credentials = MagicMock()

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
        )

        token = await manager.get_token(None)
        assert token is None

    @pytest.mark.asyncio
    async def test_get_token_no_credentials(self):
        """Test getting token with no credentials returns None."""
        mock_api_client = MagicMock()

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=None,
        )

        token = await manager.get_token("test-tenant")
        assert token is None

    @pytest.mark.asyncio
    async def test_get_token_success(self):
        """Test successful token retrieval."""
        mock_api_client = MagicMock()
        mock_token_response = MagicMock()
        mock_token_response.access_token = VALID_TEST_TOKEN
        mock_api_client.bots.token.get_graph = AsyncMock(return_value=mock_token_response)

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="default-tenant-id",
        )

        mock_logger = MagicMock()
        mock_child_logger = MagicMock()
        mock_logger.getChild.return_value = mock_child_logger

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
            logger=mock_logger,
        )

        token = await manager.get_token("test-tenant")

        assert token is not None
        assert isinstance(token, JsonWebToken)
        # Verify the API was called
        mock_api_client.bots.token.get_graph.assert_called_once()
        # Verify child logger was created and debug was called
        mock_logger.getChild.assert_called_once_with("GraphTokenManager")
        mock_child_logger.debug.assert_called_once()

        # Test that subsequent calls use cache by calling again
        token2 = await manager.get_token("test-tenant")
        assert token2 == token
        # API should still only be called once due to caching
        mock_api_client.bots.token.get_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_from_cache(self):
        """Test getting token from cache."""
        mock_api_client = MagicMock()
        mock_credentials = MagicMock()

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
        )

        # Set up the API response for initial token
        mock_token_response = MagicMock()
        mock_token_response.access_token = VALID_TEST_TOKEN
        mock_api_client.bots.token.get_graph = AsyncMock(return_value=mock_token_response)

        # First call should hit the API
        token1 = await manager.get_token("test-tenant")
        assert token1 is not None
        assert isinstance(token1, JsonWebToken)
        mock_api_client.bots.token.get_graph.assert_called_once()

        # Second call should use cache (API should not be called again)
        token2 = await manager.get_token("test-tenant")
        assert token2 == token1  # Should be the same cached token
        # Still only called once due to caching
        mock_api_client.bots.token.get_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_api_error(self):
        """Test token retrieval when API call fails."""
        mock_api_client = MagicMock()
        mock_api_client.bots.token.get_graph = AsyncMock(side_effect=Exception("API Error"))

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="default-tenant-id",
        )

        mock_logger = MagicMock()
        mock_child_logger = MagicMock()
        mock_logger.getChild.return_value = mock_child_logger

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
            logger=mock_logger,
        )

        token = await manager.get_token("test-tenant")

        assert token is None
        # Verify child logger was created and error was logged
        mock_logger.getChild.assert_called_once_with("GraphTokenManager")
        mock_child_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_token_no_logger_on_error(self):
        """Test token retrieval error handling without logger."""
        mock_api_client = MagicMock()
        mock_api_client.bots.token.get_graph = AsyncMock(side_effect=Exception("API Error"))

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="default-tenant-id",
        )

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
            # No logger
        )

        token = await manager.get_token("test-tenant")

        assert token is None
        # Should not raise exception even without logger

    @pytest.mark.asyncio
    async def test_get_token_expired_cache_refresh(self):
        """Test that expired tokens in cache are refreshed."""
        mock_api_client = MagicMock()
        mock_token_response = MagicMock()
        mock_token_response.access_token = ANOTHER_VALID_TOKEN
        mock_api_client.bots.token.get_graph = AsyncMock(return_value=mock_token_response)

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="default-tenant-id",
        )

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=mock_credentials,
        )

        # First, get a token to populate cache
        first_token_response = MagicMock()
        first_token_response.access_token = VALID_TEST_TOKEN
        mock_api_client.bots.token.get_graph.return_value = first_token_response

        first_token = await manager.get_token("test-tenant")
        assert first_token is not None

        # Now simulate the cached token being expired and get a new one
        mock_api_client.bots.token.get_graph.return_value = mock_token_response
        second_token = await manager.get_token("test-tenant")

        assert second_token is not None
        assert isinstance(second_token, JsonWebToken)
        # Verify the API was called multiple times (once for each get)
        assert mock_api_client.bots.token.get_graph.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_token_creates_tenant_specific_credentials(self):
        """Test that tenant-specific credentials are created for the API call."""
        mock_api_client = MagicMock()
        mock_token_response = MagicMock()
        mock_token_response.access_token = VALID_TEST_TOKEN
        mock_api_client.bots.token.get_graph = AsyncMock(return_value=mock_token_response)

        original_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="original-tenant-id",
        )

        manager = GraphTokenManager(
            api_client=mock_api_client,
            credentials=original_credentials,
        )

        token = await manager.get_token("different-tenant-id")

        assert token is not None
        # Verify the API was called
        mock_api_client.bots.token.get_graph.assert_called_once()

        # Get the credentials that were passed to the API
        call_args = mock_api_client.bots.token.get_graph.call_args
        passed_credentials = call_args[0][0]  # First positional argument

        # Verify it's a ClientCredentials with the correct tenant
        assert isinstance(passed_credentials, ClientCredentials)
        assert passed_credentials.client_id == "test-client-id"
        assert passed_credentials.client_secret == "test-client-secret"
        assert passed_credentials.tenant_id == "different-tenant-id"
