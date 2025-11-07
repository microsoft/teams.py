"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock, create_autospec, patch

import pytest
from microsoft.teams.api import ClientCredentials, JsonWebToken, ManagedIdentityCredentials
from microsoft.teams.apps.token_manager import TokenManager
from msal import ManagedIdentityClient  # pyright: ignore[reportMissingTypeStubs]

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
        """Test successful bot token retrieval using MSAL."""
        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="test-tenant-id",
        )

        # Mock MSAL ConfidentialClientApplication
        mock_msal_app = MagicMock()
        mock_msal_app.acquire_token_for_client = MagicMock(return_value={"access_token": VALID_TEST_TOKEN})

        with patch(
            "microsoft.teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
        ) as mock_msal_class:
            manager = TokenManager(credentials=mock_credentials)

            token = await manager.get_bot_token()

            assert token is not None
            assert isinstance(token, JsonWebToken)
            assert str(token) == VALID_TEST_TOKEN

            # Verify MSAL was called with correct scope
            mock_msal_app.acquire_token_for_client.assert_called_once_with(["https://api.botframework.com/.default"])

            # Verify MSAL app was created with the credentials tenant_id
            mock_msal_class.assert_called_once_with(
                "test-client-id",
                client_credential="test-client-secret",
                authority="https://login.microsoftonline.com/test-tenant-id",
            )

    @pytest.mark.asyncio
    async def test_get_bot_token_no_credentials(self):
        """Test getting bot token with no credentials returns None."""
        manager = TokenManager(credentials=None)
        token = await manager.get_bot_token()
        assert token is None

    @pytest.mark.asyncio
    async def test_get_bot_token_default_tenant(self):
        """Test bot token uses default tenant when credentials have no tenant_id."""
        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id=None,
        )

        # Mock MSAL ConfidentialClientApplication
        mock_msal_app = MagicMock()
        mock_msal_app.acquire_token_for_client = MagicMock(return_value={"access_token": VALID_TEST_TOKEN})

        with patch(
            "microsoft.teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
        ) as mock_msal_class:
            manager = TokenManager(credentials=mock_credentials)

            token = await manager.get_bot_token()

            assert token is not None
            assert isinstance(token, JsonWebToken)

            # Verify MSAL app was created with default bot token tenant
            mock_msal_class.assert_called_once_with(
                "test-client-id",
                client_credential="test-client-secret",
                authority="https://login.microsoftonline.com/botframework.com",
            )

    @pytest.mark.asyncio
    async def test_get_graph_token_default(self):
        """Test getting default graph token using MSAL."""
        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="default-tenant-id",
        )

        # Mock MSAL ConfidentialClientApplication
        mock_msal_app = MagicMock()
        mock_msal_app.acquire_token_for_client = MagicMock(return_value={"access_token": VALID_TEST_TOKEN})

        with patch(
            "microsoft.teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
        ) as mock_msal_class:
            manager = TokenManager(credentials=mock_credentials)

            token = await manager.get_graph_token()

            assert token is not None
            assert isinstance(token, JsonWebToken)
            assert str(token) == VALID_TEST_TOKEN

            # Verify MSAL was called with correct scope
            mock_msal_app.acquire_token_for_client.assert_called_once_with(["https://graph.microsoft.com/.default"])

            # Verify MSAL app was created with the credentials tenant_id
            mock_msal_class.assert_called_once_with(
                "test-client-id",
                client_credential="test-client-secret",
                authority="https://login.microsoftonline.com/default-tenant-id",
            )

    @pytest.mark.asyncio
    async def test_get_graph_token_default_tenant(self):
        """Test graph token uses default tenant when credentials have no tenant_id."""
        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id=None,
        )

        # Mock MSAL ConfidentialClientApplication
        mock_msal_app = MagicMock()
        mock_msal_app.acquire_token_for_client = MagicMock(return_value={"access_token": VALID_TEST_TOKEN})

        with patch(
            "microsoft.teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
        ) as mock_msal_class:
            manager = TokenManager(credentials=mock_credentials)

            token = await manager.get_graph_token()

            assert token is not None
            assert isinstance(token, JsonWebToken)

            # Verify MSAL app was created with default graph token tenant "common"
            mock_msal_class.assert_called_once_with(
                "test-client-id",
                client_credential="test-client-secret",
                authority="https://login.microsoftonline.com/common",
            )

    @pytest.mark.asyncio
    async def test_get_graph_token_with_tenant(self):
        """Test getting tenant-specific graph token using MSAL."""
        original_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="original-tenant-id",
        )

        # Mock MSAL ConfidentialClientApplication
        mock_msal_app = MagicMock()
        mock_msal_app.acquire_token_for_client = MagicMock(return_value={"access_token": VALID_TEST_TOKEN})

        with patch(
            "microsoft.teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
        ) as mock_msal_class:
            manager = TokenManager(credentials=original_credentials)

            token = await manager.get_graph_token("different-tenant-id")

            assert token is not None
            assert isinstance(token, JsonWebToken)

            # Verify MSAL app was created with different tenant ID
            # The manager caches MSAL clients, so we check the call to the class constructor
            calls = mock_msal_class.call_args_list
            # Should have been called with different-tenant-id
            assert any("different-tenant-id" in str(call) for call in calls)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "get_token_method,expected_resource",
        [
            ("get_bot_token", "https://api.botframework.com"),
            ("get_graph_token", "https://graph.microsoft.com"),
        ],
    )
    async def test_get_token_with_managed_identity(self, get_token_method: str, expected_resource: str):
        """Test token retrieval using ManagedIdentityCredentials."""
        mock_credentials = ManagedIdentityCredentials(
            client_id="test-managed-identity-client-id",
            tenant_id="test-tenant-id",
        )

        # Create a mock that will pass isinstance checks
        mock_msal_client = create_autospec(ManagedIdentityClient, instance=True)
        mock_msal_client.acquire_token_for_client.return_value = {"access_token": VALID_TEST_TOKEN}

        manager = TokenManager(credentials=mock_credentials)

        # Patch _get_msal_client to return our mock
        with patch.object(manager, "_get_msal_client", return_value=mock_msal_client):
            # Call the method dynamically
            token = await getattr(manager, get_token_method)()

            assert token is not None
            assert isinstance(token, JsonWebToken)
            assert str(token) == VALID_TEST_TOKEN

            # Verify MSAL was called with resource parameter (not scopes list)
            # and without /.default suffix
            mock_msal_client.acquire_token_for_client.assert_called_once_with(resource=expected_resource)

    @pytest.mark.asyncio
    async def test_get_graph_token_with_managed_identity_and_tenant(self):
        """Test getting tenant-specific graph token with ManagedIdentityCredentials."""
        mock_credentials = ManagedIdentityCredentials(
            client_id="test-managed-identity-client-id",
            tenant_id="original-tenant-id",
        )

        # Create a mock that will pass isinstance checks
        mock_msal_client = create_autospec(ManagedIdentityClient, instance=True)
        mock_msal_client.acquire_token_for_client.return_value = {"access_token": VALID_TEST_TOKEN}

        manager = TokenManager(credentials=mock_credentials)

        # Track calls to _get_msal_client
        get_msal_client_calls: list[str] = []

        def track_get_msal_client(tenant_id: str):
            get_msal_client_calls.append(tenant_id)
            return mock_msal_client

        # Patch _get_msal_client to track calls
        with patch.object(manager, "_get_msal_client", side_effect=track_get_msal_client):
            # Request token for different tenant
            token = await manager.get_graph_token("different-tenant-id")

            assert token is not None
            assert isinstance(token, JsonWebToken)

            # Verify _get_msal_client was called with different-tenant-id
            assert "different-tenant-id" in get_msal_client_calls

    @pytest.mark.asyncio
    async def test_get_token_error_handling_with_managed_identity(self):
        """Test error handling when token acquisition fails with ManagedIdentityCredentials."""
        mock_credentials = ManagedIdentityCredentials(
            client_id="test-managed-identity-client-id",
            tenant_id="test-tenant-id",
        )

        # Create a mock that returns an error
        mock_msal_client = create_autospec(ManagedIdentityClient, instance=True)
        mock_msal_client.acquire_token_for_client.return_value = {
            "error": "invalid_client",
            "error_description": "Invalid managed identity configuration",
        }

        manager = TokenManager(credentials=mock_credentials)

        # Patch _get_msal_client to return our mock
        with patch.object(manager, "_get_msal_client", return_value=mock_msal_client):
            # Should raise an error when token acquisition fails
            with pytest.raises(ValueError) as exc_info:
                await manager.get_bot_token()

            assert "invalid_client" in str(exc_info.value)
