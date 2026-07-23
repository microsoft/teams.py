"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Literal, cast
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import pytest
from microsoft_teams.api import (
    AgenticUser,
    ClientCredentials,
    FederatedIdentityCredentials,
    JsonWebToken,
    ManagedIdentityCredentials,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.auth.credentials import TokenCredentials
from microsoft_teams.apps.auth_provider import AppAuthProvider
from microsoft_teams.apps.token_manager import AGENT_BOT_API_SCOPE, TOKEN_EXCHANGE_SCOPE, TokenManager
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
    async def test_get_agentic_user_token_uses_agent_identity_flow(self):
        mock_credentials = ClientCredentials(
            client_id="blueprint-client-id",
            client_secret="blueprint-client-secret",
            tenant_id="tenant-id",
        )

        blueprint_app = MagicMock()
        blueprint_app.acquire_token_for_client.return_value = {"access_token": "t1-token"}

        agent_app = MagicMock()
        agent_app.acquire_token_for_client.side_effect = lambda _scopes: (
            mock_confidential_app.call_args_list[1].kwargs["client_credential"]["client_assertion"]({}),
            {"access_token": "t2-token"},
        )[1]
        agent_app.acquire_token_by_user_federated_identity_credential.return_value = {"access_token": VALID_TEST_TOKEN}

        with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_confidential_app:
            mock_confidential_app.side_effect = [blueprint_app, agent_app]

            manager = TokenManager(credentials=mock_credentials)
            token = await manager.get_agentic_user_token(
                AGENT_BOT_API_SCOPE,
                AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id"),
            )

        assert token is not None
        assert str(token) == VALID_TEST_TOKEN

        blueprint_app.acquire_token_for_client.assert_called_once_with(
            [TOKEN_EXCHANGE_SCOPE], fmi_path="agentic-app-instance-id"
        )
        agent_app.acquire_token_for_client.assert_called_once_with([TOKEN_EXCHANGE_SCOPE])
        agent_app.acquire_token_by_user_federated_identity_credential.assert_called_once_with(
            [AGENT_BOT_API_SCOPE],
            assertion="t2-token",
            user_object_id="agentic-user-id",
            username=None,
            data={"requested_token_use": "on_behalf_of"},
        )

        first_call, second_call = mock_confidential_app.call_args_list
        assert first_call.args == ("blueprint-client-id",)
        assert first_call.kwargs == {
            "client_credential": "blueprint-client-secret",
            "authority": "https://login.microsoftonline.com/tenant-id",
        }
        assert second_call.args == ("agentic-app-instance-id",)
        assert second_call.kwargs["authority"] == "https://login.microsoftonline.com/tenant-id"
        assert callable(second_call.kwargs["client_credential"]["client_assertion"])

    @pytest.mark.asyncio
    async def test_get_agentic_user_token_caches_agent_identity_client(self):
        mock_credentials = ClientCredentials(
            client_id="blueprint-client-id",
            client_secret="blueprint-client-secret",
            tenant_id="tenant-id",
        )

        blueprint_app = MagicMock()
        blueprint_app.acquire_token_for_client.return_value = {"access_token": "t1-token"}

        agent_app = MagicMock()
        agent_app.acquire_token_for_client.return_value = {"access_token": "t2-token"}
        agent_app.acquire_token_by_user_federated_identity_credential.return_value = {"access_token": VALID_TEST_TOKEN}

        with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_confidential_app:
            mock_confidential_app.side_effect = [blueprint_app, agent_app]

            manager = TokenManager(credentials=mock_credentials)
            await manager.get_agentic_user_token(
                AGENT_BOT_API_SCOPE, AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
            )
            await manager.get_agentic_user_token(
                AGENT_BOT_API_SCOPE, AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
            )

        assert mock_confidential_app.call_count == 2

    @pytest.mark.asyncio
    async def test_get_agentic_user_token_with_token_credentials_passes_agentic_user(self):
        calls = []

        async def token_provider(scope: str, tenant_id: str | None, *, agentic_user: AgenticUser | None):
            calls.append((scope, tenant_id, agentic_user))
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(client_id="blueprint-client-id", token=token_provider, tenant_id="tenant-id")
        manager = TokenManager(credentials=credentials)

        identity = AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
        token = await manager.get_agentic_user_token(AGENT_BOT_API_SCOPE, identity)

        assert token is not None
        assert str(token) == VALID_TEST_TOKEN
        assert calls == [(AGENT_BOT_API_SCOPE, "tenant-id", identity)]

    @pytest.mark.asyncio
    async def test_get_agentic_user_token_with_token_credentials_accepts_positional_identity(self):
        calls = []

        def token_provider(scope: str, tenant_id: str | None, identity: AgenticUser | None):
            calls.append((scope, tenant_id, identity))
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(client_id="blueprint-client-id", token=token_provider, tenant_id="tenant-id")
        manager = TokenManager(credentials=credentials)

        identity = AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
        token = await manager.get_agentic_user_token(AGENT_BOT_API_SCOPE, identity)

        assert token is not None
        assert str(token) == VALID_TEST_TOKEN
        assert calls == [(AGENT_BOT_API_SCOPE, "tenant-id", identity)]

    @pytest.mark.asyncio
    async def test_get_token_with_required_third_argument_passes_none_for_non_agentic_user_token(self):
        calls = []

        def token_provider(scope: str, tenant_id: str | None, identity: AgenticUser | None):
            calls.append((scope, tenant_id, identity))
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(client_id="test-client-id", token=token_provider, tenant_id="tenant-id")
        manager = TokenManager(credentials=credentials)

        token = await manager._get_token_with_token_provider(credentials, AGENT_BOT_API_SCOPE, "tenant-id")

        assert str(token) == VALID_TEST_TOKEN
        assert calls == [(AGENT_BOT_API_SCOPE, "tenant-id", None)]

    @pytest.mark.asyncio
    async def test_get_token_with_optional_third_argument_uses_default_for_non_agentic_user_token(self):
        calls = []

        def token_provider(scope: str, tenant_id: str | None, timeout: int = 30):
            calls.append((scope, tenant_id, timeout))
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(client_id="test-client-id", token=token_provider, tenant_id="tenant-id")
        manager = TokenManager(credentials=credentials)

        token = await manager._get_token_with_token_provider(credentials, AGENT_BOT_API_SCOPE, "tenant-id")

        assert str(token) == VALID_TEST_TOKEN
        assert calls == [(AGENT_BOT_API_SCOPE, "tenant-id", 30)]

    @pytest.mark.asyncio
    async def test_token_provider_uninspectable_signature_uses_legacy_args_without_agentic_user(self):
        calls = []

        def token_provider(scope: str, tenant_id: str | None):
            calls.append((scope, tenant_id))
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(client_id="test-client-id", token=token_provider, tenant_id="tenant-id")
        manager = TokenManager(credentials=credentials)

        with patch("microsoft_teams.apps.token_manager.signature", side_effect=ValueError("no signature")):
            token = await manager._get_token_with_token_provider(credentials, AGENT_BOT_API_SCOPE, "tenant-id")

        assert str(token) == VALID_TEST_TOKEN
        assert calls == [(AGENT_BOT_API_SCOPE, "tenant-id")]

    @pytest.mark.asyncio
    async def test_token_provider_uninspectable_signature_rejects_agentic_user(self):
        credentials = TokenCredentials(
            client_id="test-client-id",
            token=lambda _scope, _tenant_id: VALID_TEST_TOKEN,
            tenant_id="tenant-id",
        )
        manager = TokenManager(credentials=credentials)
        agentic_user = AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")

        with patch("microsoft_teams.apps.token_manager.signature", side_effect=ValueError("no signature")):
            with pytest.raises(ValueError, match="Token provider must accept agentic_user"):
                await manager._get_token_with_token_provider(
                    credentials, AGENT_BOT_API_SCOPE, "tenant-id", agentic_user
                )

    @pytest.mark.asyncio
    async def test_app_auth_provider_uses_app_token_without_agentic_user(self):
        token_manager = MagicMock(spec=TokenManager)
        token_manager.get_app_token = AsyncMock(return_value="app-token")
        auth_provider = AppAuthProvider(token_manager, PUBLIC)

        token = await auth_provider.token()

        assert token == "app-token"
        token_manager.get_app_token.assert_awaited_once_with(PUBLIC.bot_scope, caller_name="token")
        token_manager.get_agentic_user_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_app_auth_provider_uses_agentic_user_token_with_agentic_user(self):
        token_manager = MagicMock(spec=TokenManager)
        token_manager.get_agentic_user_token = AsyncMock(return_value="agentic-user-token")
        auth_provider = AppAuthProvider(token_manager, PUBLIC)
        agentic_user = AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")

        token = await auth_provider.token(agentic_user=agentic_user)

        assert token == "agentic-user-token"
        token_manager.get_agentic_user_token.assert_awaited_once_with(
            AGENT_BOT_API_SCOPE,
            agentic_user,
            caller_name="token",
        )
        token_manager.get_app_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_app_auth_provider_passes_missing_agentic_user_tenant_to_token_manager(self):
        token_manager = MagicMock(spec=TokenManager)
        token_manager.get_agentic_user_token = AsyncMock(return_value="agentic-user-token")
        auth_provider = AppAuthProvider(token_manager, PUBLIC)
        agentic_user = AgenticUser("agentic-app-instance-id", "agentic-user-id")

        token = await auth_provider.token(agentic_user=agentic_user)

        assert token == "agentic-user-token"
        token_manager.get_agentic_user_token.assert_awaited_once_with(
            AGENT_BOT_API_SCOPE,
            agentic_user,
            caller_name="token",
        )
        token_manager.get_app_token.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_agentic_user_token_uses_credentials_tenant_when_missing(self):
        calls = []

        async def token_provider(scope: str, tenant_id: str | None, *, agentic_user: AgenticUser | None):
            calls.append((scope, tenant_id, agentic_user))
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(
            client_id="blueprint-client-id", token=token_provider, tenant_id="credential-tenant-id"
        )
        manager = TokenManager(credentials=credentials)

        identity = AgenticUser("agentic-app-instance-id", "agentic-user-id")
        token = await manager.get_agentic_user_token(AGENT_BOT_API_SCOPE, identity)

        assert token is not None
        assert calls == [(AGENT_BOT_API_SCOPE, "credential-tenant-id", identity)]

    @pytest.mark.asyncio
    async def test_get_agentic_user_token_requires_tenant_when_missing_from_request_and_credentials(self):
        credentials = TokenCredentials(
            client_id="blueprint-client-id",
            token=lambda _scope, _tenant_id: VALID_TEST_TOKEN,
        )
        manager = TokenManager(credentials=credentials)

        with pytest.raises(ValueError, match="tenant_id is required to get an agentic user token"):
            await manager.get_agentic_user_token(
                AGENT_BOT_API_SCOPE,
                AgenticUser("agentic-app-instance-id", "agentic-user-id"),
            )

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
            "microsoft_teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
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
            "microsoft_teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
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
            "microsoft_teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
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
            "microsoft_teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
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
            "microsoft_teams.apps.token_manager.ConfidentialClientApplication", return_value=mock_msal_app
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

        # Patch _get_managed_identity_client to return our mock
        with patch.object(manager, "_get_managed_identity_client", return_value=mock_msal_client):
            # Call the method dynamically
            token = await getattr(manager, get_token_method)()

            assert token is not None
            assert isinstance(token, JsonWebToken)
            assert str(token) == VALID_TEST_TOKEN

            # Verify MSAL was called with resource parameter (not scopes list)
            # and without /.default suffix
            mock_msal_client.acquire_token_for_client.assert_called_once_with(resource=expected_resource)

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

        # Patch _get_managed_identity_client to return our mock
        with patch.object(manager, "_get_managed_identity_client", return_value=mock_msal_client):
            # Should raise an error when token acquisition fails
            with pytest.raises(ValueError) as exc_info:
                await manager.get_bot_token()

            assert "invalid_client" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mi_type,mi_client_id,description",
        [
            ("system", None, "system-assigned managed identity"),
            ("user", "test-user-mi-client-id", "user-assigned managed identity"),
        ],
    )
    async def test_get_token_with_federated_identity(self, mi_type: str, mi_client_id: str | None, description: str):
        """Test token retrieval using FederatedIdentityCredentials (two-step flow)."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type=cast(Literal["system", "user"], mi_type),
            managed_identity_client_id=mi_client_id,
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        # Mock the managed identity token acquisition used by the lazy client_assertion callback
        mi_token = "mi_token_from_step_1"
        with patch.object(manager, "_acquire_managed_identity_token_sync", return_value=mi_token):
            # Mock ConfidentialClientApplication for step 2
            with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_confidential_app:
                mock_app_instance = MagicMock()
                mock_app_instance.acquire_token_for_client.return_value = {"access_token": VALID_TEST_TOKEN}
                mock_confidential_app.return_value = mock_app_instance

                token = await manager.get_bot_token()

                assert token is not None, f"Failed for: {description}"
                assert isinstance(token, JsonWebToken), f"Failed for: {description}"
                assert str(token) == VALID_TEST_TOKEN, f"Failed for: {description}"

                # Verify ConfidentialClientApplication was called with a lazy client_assertion callback
                mock_confidential_app.assert_called_once()
                call_kwargs = mock_confidential_app.call_args[1]
                client_assertion = call_kwargs["client_credential"]["client_assertion"]
                assert callable(client_assertion), f"Failed for: {description}"
                assert client_assertion() == mi_token, f"Failed for: {description}"

    @pytest.mark.asyncio
    async def test_get_token_with_federated_identity_step1_failure(self):
        """Test error handling when step 1 (MI token acquisition) fails."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="user",
            managed_identity_client_id="test-mi-client-id",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        # Mock step 1 to fail when MSAL invokes the lazy client_assertion callback
        with patch.object(
            manager, "_acquire_managed_identity_token_sync", side_effect=ValueError("MI token acquisition failed")
        ):
            with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_confidential_app:
                mock_app_instance = MagicMock()

                def acquire_token_for_client(_scopes):
                    client_credential = mock_confidential_app.call_args.kwargs["client_credential"]
                    client_credential["client_assertion"]()

                mock_app_instance.acquire_token_for_client.side_effect = acquire_token_for_client
                mock_confidential_app.return_value = mock_app_instance

                with pytest.raises(ValueError) as exc_info:
                    await manager.get_bot_token()

            assert "MI token acquisition failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_token_with_federated_identity_step2_failure(self):
        """Test error handling when step 2 (final token acquisition) fails."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="user",
            managed_identity_client_id="test-mi-client-id",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        # Mock step 1 to succeed
        mi_token = "mi_token_from_step_1"
        with patch.object(manager, "_acquire_managed_identity_token_sync", return_value=mi_token):
            # Mock step 2 to fail
            with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_confidential_app:
                mock_app_instance = MagicMock()
                mock_app_instance.acquire_token_for_client.return_value = {
                    "error": "invalid_grant",
                    "error_description": "FIC Step 2 failed",
                }
                mock_confidential_app.return_value = mock_app_instance

                with pytest.raises(ValueError) as exc_info:
                    await manager.get_bot_token()

                assert "invalid_grant" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_token_caller_name_logged_when_no_credentials(self):
        """Test that caller_name is logged when credentials is None (covers line 77)."""
        manager = TokenManager(credentials=None)

        # Call _get_token directly with caller_name set and credentials=None
        result = await manager._get_token(
            "https://api.botframework.com/.default", "botframework.com", caller_name="test_caller"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_token_with_token_credentials_sync(self):
        """Test _get_token with a synchronous TokenCredentials token provider."""
        credentials = TokenCredentials(
            client_id="test-client-id",
            token=lambda scope, tenant: VALID_TEST_TOKEN,
            tenant_id="tenant",
        )
        manager = TokenManager(credentials=credentials)

        result = await manager._get_token("https://api.botframework.com/.default", "botframework.com")
        assert result is not None
        assert isinstance(result, JsonWebToken)
        assert str(result) == VALID_TEST_TOKEN

    @pytest.mark.asyncio
    async def test_get_token_with_token_credentials_async(self):
        """Test _get_token with an async TokenCredentials token provider."""

        async def async_token_provider(scope: str | list[str], _tenant: str | None) -> str:
            return VALID_TEST_TOKEN

        credentials = TokenCredentials(
            client_id="test-client-id",
            token=async_token_provider,
            tenant_id="tenant",
        )
        manager = TokenManager(credentials=credentials)

        result = await manager._get_token("https://api.botframework.com/.default", "botframework.com")
        assert result is not None
        assert isinstance(result, JsonWebToken)
        assert str(result) == VALID_TEST_TOKEN

    @pytest.mark.asyncio
    async def test_acquire_managed_identity_token_success(self):
        """Test _acquire_managed_identity_token returns token string on success."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="user",
            managed_identity_client_id="test-mi-client-id",
            tenant_id="test-tenant-id",
        )

        mock_mi_client = create_autospec(ManagedIdentityClient, instance=True)
        mock_mi_client.acquire_token_for_client.return_value = {"access_token": "mi-token"}

        manager = TokenManager(credentials=mock_credentials)

        with patch.object(manager, "_get_managed_identity_client", return_value=mock_mi_client):
            result = await manager._acquire_managed_identity_token(mock_credentials)

        assert result == "mi-token"
        mock_mi_client.acquire_token_for_client.assert_called_once_with(resource="api://AzureADTokenExchange")

    @pytest.mark.asyncio
    async def test_acquire_managed_identity_token_failure(self):
        """Test _acquire_managed_identity_token raises ValueError when no access_token returned."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="user",
            managed_identity_client_id="test-mi-client-id",
            tenant_id="test-tenant-id",
        )

        mock_mi_client = create_autospec(ManagedIdentityClient, instance=True)
        mock_mi_client.acquire_token_for_client.return_value = {"error": "some_error"}

        manager = TokenManager(credentials=mock_credentials)

        with patch.object(manager, "_get_managed_identity_client", return_value=mock_mi_client):
            with pytest.raises(ValueError) as exc_info:
                await manager._acquire_managed_identity_token(mock_credentials)

        assert "some_error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_confidential_client_uses_cache(self):
        """Test that _get_confidential_client returns cached client on second call."""
        mock_credentials = ClientCredentials(
            client_id="test-client-id",
            client_secret="test-client-secret",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_msal_class:
            mock_msal_class.return_value = MagicMock()

            client_first = manager._get_confidential_client(mock_credentials, "test-tenant-id")
            client_second = manager._get_confidential_client(mock_credentials, "test-tenant-id")

        # ConfidentialClientApplication should only be constructed once
        mock_msal_class.assert_called_once()
        assert client_first is client_second

    @pytest.mark.asyncio
    async def test_get_managed_identity_client_uses_cache(self):
        """Test that _get_managed_identity_client returns cached client on second call."""
        mock_credentials = ManagedIdentityCredentials(
            client_id="test-managed-identity-client-id",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        with patch("microsoft_teams.apps.token_manager.ManagedIdentityClient") as mock_mi_client_class:
            with patch("microsoft_teams.apps.token_manager.requests") as mock_requests:
                mock_requests.Session.return_value = MagicMock()
                mock_mi_client_class.return_value = MagicMock()

                client_first = manager._get_managed_identity_client(mock_credentials)
                client_second = manager._get_managed_identity_client(mock_credentials)

        # ManagedIdentityClient should only be constructed once
        mock_mi_client_class.assert_called_once()
        assert client_first is client_second

    @pytest.mark.asyncio
    async def test_get_federated_identity_client_uses_cache(self):
        """Test that _get_federated_identity_client returns cached client on second call."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="user",
            managed_identity_client_id="test-mi-client-id",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        with patch("microsoft_teams.apps.token_manager.ConfidentialClientApplication") as mock_msal_class:
            mock_msal_class.return_value = MagicMock()

            client_first = manager._get_federated_identity_client(mock_credentials, "test-tenant-id")
            client_second = manager._get_federated_identity_client(mock_credentials, "test-tenant-id")

        mock_msal_class.assert_called_once()
        assert client_first is client_second

    @pytest.mark.asyncio
    async def test_get_managed_identity_client_with_managed_identity_credentials(self):
        """Test _get_managed_identity_client creates UserAssignedManagedIdentity for ManagedIdentityCredentials."""
        mock_credentials = ManagedIdentityCredentials(
            client_id="test-managed-identity-client-id",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        with patch("microsoft_teams.apps.token_manager.ManagedIdentityClient") as mock_mi_client_class:
            with patch("microsoft_teams.apps.token_manager.requests") as mock_requests:
                mock_requests.Session.return_value = MagicMock()
                mock_mi_client_class.return_value = MagicMock()
                with patch("microsoft_teams.apps.token_manager.UserAssignedManagedIdentity") as mock_user_mi:
                    mock_user_mi.return_value = MagicMock()

                    manager._get_managed_identity_client(mock_credentials)

                    mock_user_mi.assert_called_once_with(client_id="test-managed-identity-client-id")

    @pytest.mark.asyncio
    async def test_get_managed_identity_client_with_federated_system(self):
        """Test _get_managed_identity_client uses SystemAssignedManagedIdentity for system managed_identity_type."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="system",
            managed_identity_client_id=None,
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        with patch("microsoft_teams.apps.token_manager.ManagedIdentityClient") as mock_mi_client_class:
            with patch("microsoft_teams.apps.token_manager.requests") as mock_requests:
                mock_requests.Session.return_value = MagicMock()
                mock_mi_client_class.return_value = MagicMock()
                with patch("microsoft_teams.apps.token_manager.SystemAssignedManagedIdentity") as mock_system_mi:
                    mock_system_mi.return_value = MagicMock()

                    manager._get_managed_identity_client(mock_credentials)

                    mock_system_mi.assert_called_once_with()

    @pytest.mark.asyncio
    async def test_get_managed_identity_client_with_federated_user(self):
        """Test _get_managed_identity_client uses UserAssignedManagedIdentity with mi_client_id for user type."""
        mock_credentials = FederatedIdentityCredentials(
            client_id="test-app-client-id",
            managed_identity_type="user",
            managed_identity_client_id="mi-client",
            tenant_id="test-tenant-id",
        )

        manager = TokenManager(credentials=mock_credentials)

        with patch("microsoft_teams.apps.token_manager.ManagedIdentityClient") as mock_mi_client_class:
            with patch("microsoft_teams.apps.token_manager.requests") as mock_requests:
                mock_requests.Session.return_value = MagicMock()
                mock_mi_client_class.return_value = MagicMock()
                with patch("microsoft_teams.apps.token_manager.UserAssignedManagedIdentity") as mock_user_mi:
                    mock_user_mi.return_value = MagicMock()

                    manager._get_managed_identity_client(mock_credentials)

                    mock_user_mi.assert_called_once_with(client_id="mi-client")
