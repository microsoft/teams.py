"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft.teams.api import ClientCredentials, JsonWebToken
from microsoft.teams.apps.token_manager import TokenManager
from microsoft.teams.common import Client

# Valid JWT-like token for testing (format: header.payload.signature)
VALID_TEST_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)


class TestTokenManager:
    """Test TokenManager functionality."""

    @pytest.mark.asyncio
    async def test_get_bot_token_success(self):
        """Test successful bot token refresh, caching, and expiration refresh."""
        # First token response
        mock_token_response1 = MagicMock()
        mock_token_response1.access_token = VALID_TEST_TOKEN

        # Second token response for expired token
        mock_token_response2 = MagicMock()
        mock_token_response2.access_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiI5ODc2NTQzMjEwIiwibmFtZSI6IkphbmUgRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
            "Twzj7LKlhYUUe2GFRME4WOZdWq2TdayZhWjhBr1r5X4"
        )

        # Third token response for force refresh
        mock_token_response3 = MagicMock()
        mock_token_response3.access_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMTExMTExMTExIiwibmFtZSI6IkZvcmNlIFJlZnJlc2giLCJpYXQiOjE1MTYyMzkwMjJ9."
            "dQw4w9WgXcQ"
        )

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="test-tenant-id",
        )

        # Mock the BotTokenClient
        mock_bot_token_client = MagicMock()
        mock_bot_token_client.get = AsyncMock(
            side_effect=[mock_token_response1, mock_token_response2, mock_token_response3]
        )

        mock_http_client = MagicMock(spec=Client)
        mock_http_client.clone = MagicMock(return_value=mock_http_client)

        with patch("microsoft.teams.apps.token_manager.BotTokenClient", return_value=mock_bot_token_client):
            manager = TokenManager(
                http_client=mock_http_client,
                credentials=mock_credentials,
            )

            # First call
            token1 = await manager.get_bot_token()
            assert token1 is not None
            assert isinstance(token1, JsonWebToken)
            mock_bot_token_client.get.assert_called_once()

            # Second call should use cache (mock should still only be called once)
            token2 = await manager.get_bot_token()
            assert token2 == token1
            mock_bot_token_client.get.assert_called_once()  # Still only called once due to caching

            # Mock the token as expired
            token1.is_expired = MagicMock(return_value=True)

            # Third call should refresh because token is expired
            token3 = await manager.get_bot_token()
            assert token3 is not None
            assert token3 != token1  # New token
            assert mock_bot_token_client.get.call_count == 2

            # Force refresh even if not expired
            token3.is_expired = MagicMock(return_value=False)
            token4 = await manager.get_bot_token(force=True)
            assert token4 is not None
            assert mock_bot_token_client.get.call_count == 3

    @pytest.mark.asyncio
    async def test_get_bot_token_no_credentials(self):
        """Test refreshing bot token with no credentials returns None."""
        mock_http_client = MagicMock(spec=Client)
        mock_http_client.clone = MagicMock(return_value=mock_http_client)

        with patch("microsoft.teams.apps.token_manager.BotTokenClient"):
            manager = TokenManager(
                http_client=mock_http_client,
                credentials=None,
            )

            token = await manager.get_bot_token()
            assert token is None

    @pytest.mark.asyncio
    async def test_get_graph_token_default(self):
        """Test getting default graph token with caching and expiration refresh."""
        # First token response
        mock_token_response1 = MagicMock()
        mock_token_response1.access_token = VALID_TEST_TOKEN

        # Second token response for expired token
        mock_token_response2 = MagicMock()
        mock_token_response2.access_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiI5ODc2NTQzMjEwIiwibmFtZSI6IkphbmUgRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ."
            "Twzj7LKlhYUUe2GFRME4WOZdWq2TdayZhWjhBr1r5X4"
        )

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="default-tenant-id",
        )

        # Mock the BotTokenClient
        mock_bot_token_client = MagicMock()
        mock_bot_token_client.get_graph = AsyncMock(side_effect=[mock_token_response1, mock_token_response2])

        mock_http_client = MagicMock(spec=Client)
        mock_http_client.clone = MagicMock(return_value=mock_http_client)

        with patch("microsoft.teams.apps.token_manager.BotTokenClient", return_value=mock_bot_token_client):
            manager = TokenManager(
                http_client=mock_http_client,
                credentials=mock_credentials,
            )

            token1 = await manager.get_graph_token()

            assert token1 is not None
            assert isinstance(token1, JsonWebToken)

            # Verify it's cached
            token2 = await manager.get_graph_token()
            assert token2 == token1
            mock_bot_token_client.get_graph.assert_called_once()

            # Mock the token as expired
            token1.is_expired = MagicMock(return_value=True)

            # Third call should refresh because token is expired
            token3 = await manager.get_graph_token()
            assert token3 is not None
            assert token3 != token1  # New token
            assert mock_bot_token_client.get_graph.call_count == 2

    @pytest.mark.asyncio
    async def test_get_graph_token_with_tenant(self):
        """Test getting tenant-specific graph token."""
        mock_token_response = MagicMock()
        mock_token_response.access_token = VALID_TEST_TOKEN

        original_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="original-tenant-id",
        )

        # Mock the BotTokenClient
        mock_bot_token_client = MagicMock()
        mock_bot_token_client.get_graph = AsyncMock(return_value=mock_token_response)

        mock_http_client = MagicMock(spec=Client)
        mock_http_client.clone = MagicMock(return_value=mock_http_client)

        with patch("microsoft.teams.apps.token_manager.BotTokenClient", return_value=mock_bot_token_client):
            manager = TokenManager(
                http_client=mock_http_client,
                credentials=original_credentials,
            )

            token = await manager.get_graph_token("different-tenant-id")

            assert token is not None
            mock_bot_token_client.get_graph.assert_called_once()

            # Verify tenant-specific credentials were created
            call_args = mock_bot_token_client.get_graph.call_args
            passed_credentials = call_args[0][0]
            assert isinstance(passed_credentials, ClientCredentials)
            assert passed_credentials.tenant_id == "different-tenant-id"

    @pytest.mark.asyncio
    async def test_graph_token_force_refresh(self):
        """Test force refreshing graph token even when not expired."""
        mock_token_response1 = MagicMock()
        mock_token_response1.access_token = VALID_TEST_TOKEN

        mock_token_response2 = MagicMock()
        mock_token_response2.access_token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMTExMTExMTExIiwibmFtZSI6IkZvcmNlIFJlZnJlc2giLCJpYXQiOjE1MTYyMzkwMjJ9."
            "dQw4w9WgXcQ"
        )

        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="test-tenant-id",
        )

        mock_bot_token_client = MagicMock()
        mock_bot_token_client.get_graph = AsyncMock(side_effect=[mock_token_response1, mock_token_response2])

        mock_http_client = MagicMock(spec=Client)
        mock_http_client.clone = MagicMock(return_value=mock_http_client)

        with patch("microsoft.teams.apps.token_manager.BotTokenClient", return_value=mock_bot_token_client):
            manager = TokenManager(
                http_client=mock_http_client,
                credentials=mock_credentials,
            )

            # First call
            token1 = await manager.get_graph_token()
            assert token1 is not None
            mock_bot_token_client.get_graph.assert_called_once()

            # Second call should use cache
            token2 = await manager.get_graph_token()
            assert token2 == token1
            mock_bot_token_client.get_graph.assert_called_once()  # Still only called once

            # Force refresh should call API even if not expired
            token3 = await manager.get_graph_token(force=True)
            assert token3 is not None
            assert mock_bot_token_client.get_graph.call_count == 2  # Now called twice
