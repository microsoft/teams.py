"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional
from unittest.mock import MagicMock

import pytest
from microsoft.teams.api import JsonWebToken
from microsoft.teams.apps.graph_token_manager import (
    CallbackGraphTokenProvider,
    DefaultGraphTokenProvider,
    GraphTokenManager,
)

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

    def test_default_provider_initialization(self):
        """Test GraphTokenManager with default provider."""
        manager = GraphTokenManager()
        # Test that the manager has been initialized properly
        assert manager is not None

    def test_static_token_creation(self):
        """Test creating GraphTokenManager with static token."""
        token = JsonWebToken(VALID_TEST_TOKEN)
        manager = GraphTokenManager.create_with_static_token(token)
        # Test that the manager was created successfully
        assert manager is not None

    def test_callback_creation(self):
        """Test creating GraphTokenManager with callback."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return VALID_TEST_TOKEN

        manager = GraphTokenManager.create_with_callback(mock_callback)
        # Test that the manager was created successfully
        assert manager is not None

    @pytest.mark.asyncio
    async def test_get_token_with_callback_provider(self):
        """Test getting token through callback provider."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return VALID_TEST_TOKEN

        manager = GraphTokenManager.create_with_callback(mock_callback)
        token = await manager.get_token("test-tenant")

        assert token is not None
        assert isinstance(token, JsonWebToken)

    @pytest.mark.asyncio
    async def test_get_token_with_static_provider(self):
        """Test getting token through static provider."""
        static_token = JsonWebToken(VALID_TEST_TOKEN)
        manager = GraphTokenManager.create_with_static_token(static_token)
        token = await manager.get_token("test-tenant")

        assert token is static_token

    @pytest.mark.asyncio
    async def test_get_token_error_handling(self):
        """Test error handling when callback fails."""

        async def failing_callback(tenant_id: Optional[str]) -> Optional[str]:
            raise Exception("Token refresh failed")

        logger_mock = MagicMock()
        manager = GraphTokenManager.create_with_callback(failing_callback, logger_mock)
        token = await manager.get_token("test-tenant")

        assert token is None
        logger_mock.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_with_callback_provider(self):
        """Test refreshing token through callback provider."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return ANOTHER_VALID_TOKEN

        manager = GraphTokenManager.create_with_callback(mock_callback)
        token = await manager.refresh_token("test-tenant")

        assert token is not None
        assert isinstance(token, JsonWebToken)


class TestDefaultGraphTokenProvider:
    """Test DefaultGraphTokenProvider functionality."""

    @pytest.mark.asyncio
    async def test_get_token_with_static_token(self):
        """Test getting static token."""
        static_token = JsonWebToken(VALID_TEST_TOKEN)
        provider = DefaultGraphTokenProvider(static_token)
        token = await provider.get_token("test-tenant")

        assert token is static_token

    @pytest.mark.asyncio
    async def test_get_token_without_static_token(self):
        """Test getting token when no static token is set."""
        provider = DefaultGraphTokenProvider()
        token = await provider.get_token("test-tenant")

        assert token is None

    @pytest.mark.asyncio
    async def test_refresh_token_returns_static_token(self):
        """Test that refresh returns the same static token."""
        static_token = JsonWebToken(VALID_TEST_TOKEN)
        provider = DefaultGraphTokenProvider(static_token)
        token = await provider.refresh_token("test-tenant")

        assert token is static_token

    @pytest.mark.asyncio
    async def test_tenant_validation_success(self):
        """Test that tenant validation allows correct tenant."""
        static_token = JsonWebToken(VALID_TEST_TOKEN)
        provider = DefaultGraphTokenProvider(static_token, "allowed-tenant")
        token = await provider.get_token("allowed-tenant")

        assert token is static_token

    @pytest.mark.asyncio
    async def test_tenant_validation_failure(self):
        """Test that tenant validation rejects wrong tenant."""
        static_token = JsonWebToken(VALID_TEST_TOKEN)
        provider = DefaultGraphTokenProvider(static_token, "allowed-tenant")

        with pytest.raises(
            ValueError, match="Static token only valid for tenant 'allowed-tenant', requested 'wrong-tenant'"
        ):
            await provider.get_token("wrong-tenant")

    @pytest.mark.asyncio
    async def test_tenant_validation_none_tenant(self):
        """Test that tenant validation rejects None when tenant is required."""
        static_token = JsonWebToken(VALID_TEST_TOKEN)
        provider = DefaultGraphTokenProvider(static_token, "allowed-tenant")

        with pytest.raises(ValueError, match="Static token only valid for tenant 'allowed-tenant', requested 'None'"):
            await provider.get_token(None)


class TestCallbackGraphTokenProvider:
    """Test CallbackGraphTokenProvider functionality."""

    @pytest.mark.asyncio
    async def test_get_token_calls_callback(self):
        """Test that get_token calls the refresh callback."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return VALID_TEST_TOKEN

        provider = CallbackGraphTokenProvider(mock_callback)
        token = await provider.get_token("test-tenant")

        assert token is not None
        assert isinstance(token, JsonWebToken)

    @pytest.mark.asyncio
    async def test_refresh_token_calls_callback(self):
        """Test that refresh_token calls the refresh callback."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return ANOTHER_VALID_TOKEN

        provider = CallbackGraphTokenProvider(mock_callback)
        token = await provider.refresh_token("test-tenant")

        assert token is not None
        assert isinstance(token, JsonWebToken)

    @pytest.mark.asyncio
    async def test_callback_with_none_return(self):
        """Test callback returning None."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return None

        provider = CallbackGraphTokenProvider(mock_callback)
        token = await provider.get_token("test-tenant")

        assert token is None

    @pytest.mark.asyncio
    async def test_callback_error_handling(self):
        """Test error handling in callback."""

        async def failing_callback(tenant_id: Optional[str]) -> Optional[str]:
            raise Exception("Callback failed")

        logger_mock = MagicMock()
        provider = CallbackGraphTokenProvider(failing_callback, logger_mock)
        token = await provider.get_token("test-tenant")

        assert token is None
        logger_mock.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_with_invalid_token_format(self):
        """Test callback returning invalid token format."""

        async def mock_callback(tenant_id: Optional[str]) -> Optional[str]:
            return "invalid-token-format"

        logger_mock = MagicMock()
        provider = CallbackGraphTokenProvider(mock_callback, logger_mock)
        token = await provider.get_token("test-tenant")

        assert token is None
        logger_mock.error.assert_called_once()
