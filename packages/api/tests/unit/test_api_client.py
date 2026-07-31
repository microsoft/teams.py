"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import pytest
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.clients import AGENTIC_IDENTITY_CLEAR, ApiClient, ReactionClient
from microsoft_teams.api.models import AgenticIdentity
from microsoft_teams.common.http import Client, ClientOptions


class _TokenProviderAdapter:
    def get_app_token(self, scope: str, tenant_id: str | None = None):
        return self.token(scope=scope, agentic_app_id=None, agentic_user_id=None, tenant_id=tenant_id)

    def get_agentic_user_token(
        self,
        scope: str,
        agentic_app_id: str,
        agentic_user_id: str,
        tenant_id: str | None,
    ):
        return self.token(
            scope=scope,
            agentic_app_id=agentic_app_id,
            agentic_user_id=agentic_user_id,
            tenant_id=tenant_id,
        )

    def get_agentic_app_token(self, scope: str, agentic_app_id: str, tenant_id: str | None):
        return self.token(scope=scope, agentic_app_id=agentic_app_id, agentic_user_id=None, tenant_id=tenant_id)


@pytest.mark.unit
class TestApiClientReactionsProperty:
    """Tests for the reactions property on ApiClient."""

    def test_reactions_first_access_creates_reaction_client(self, mock_http_client):
        """Test that accessing reactions for the first time creates a ReactionClient."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        assert client._reactions is None

        reactions = client.reactions

        assert reactions is not None
        assert isinstance(reactions, ReactionClient)

    def test_reactions_inherits_agentic_identity_auth_defaults(self, mock_http_client):
        """Test reactions inherits agentic identity auth defaults from ApiClient."""
        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )

        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, **_kwargs):
                return "agentic-user-token"

        client = ApiClient(
            "https://mock.service.url",
            mock_http_client,
            token_provider=TestTokenProvider(),
            agentic_identity=identity,
        )

        reactions = client.reactions

        assert not hasattr(reactions, "_token_provider")
        assert not hasattr(reactions, "_agentic_identity")
        assert client.http.token is not None
        assert reactions.http is client.http

    def test_reactions_second_access_returns_cached_client(self, mock_http_client):
        """Test that the reactions property returns the same instance on subsequent accesses."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        first = client.reactions
        second = client.reactions
        assert first is second

    def test_http_setter_updates_all_sub_clients(self, mock_http_client):
        """Test that setting http propagates the new client to all sub-clients."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        new_http = Client(ClientOptions(base_url="https://new.service.url"))

        client.http = new_http

        assert client._http is new_http
        assert client._bots.http is new_http
        assert client.conversations.http is new_http
        assert client.users.http is new_http
        assert client.teams.http is new_http
        assert client.meetings.http is new_http

    def test_http_setter_without_reactions_does_not_error(self, mock_http_client):
        """Test that setting http works correctly when reactions has never been accessed."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        assert client._reactions is None

        new_http = Client(ClientOptions(base_url="https://new.service.url"))
        client.http = new_http

        assert client._http is new_http
        assert client._reactions is None

    def test_http_setter_also_updates_reactions_when_instantiated(self, mock_http_client):
        """Test that setting http propagates to the reactions client when it exists."""
        client = ApiClient("https://mock.service.url", mock_http_client)
        _ = client.reactions
        assert client._reactions is not None

        new_http = Client(ClientOptions(base_url="https://new.service.url"))
        client.http = new_http

        assert client._reactions.http is new_http
        assert client._http is new_http


@pytest.mark.unit
class TestApiClientDeprecatedAccessors:
    """The bots and reactions accessors are deprecated but still supported."""

    def test_reactions_accessor_warns(self, mock_http_client):
        client = ApiClient("https://mock.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            reactions = client.reactions
        assert isinstance(reactions, ReactionClient)

    def test_bots_accessor_warns(self, mock_http_client):
        client = ApiClient("https://mock.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            bots = client.bots
        assert bots.sign_in is not None

    @pytest.mark.asyncio
    async def test_deprecated_reactions_add_still_routes(self, mock_http_client):
        client = ApiClient("https://mock.service.url", mock_http_client)
        with pytest.warns(DeprecationWarning):
            reactions = client.reactions

        with patch.object(reactions.http, "put", new_callable=AsyncMock) as mock_put:
            await reactions.add("conv-1", "act-1", "like")

        mock_put.assert_called_once_with(
            "https://mock.service.url/v3/conversations/conv-1/activities/act-1/reactions/like"
        )


@pytest.mark.unit
class TestApiClientScoping:
    def test_clone_preserves_defaults_when_omitted(self, mock_http_client):
        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        client = ApiClient("https://mock.service.url", mock_http_client, agentic_identity=identity)

        clone = client.clone()

        assert clone.service_url == "https://mock.service.url"
        assert clone._default_agentic_identity is identity
        assert clone._api_client_settings is client._api_client_settings
        assert clone._cloud is client._cloud

    def test_clone_reuses_underlying_http_client_when_agentic_identity_is_unchanged(self, mock_http_client):
        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, **_kwargs):
                return "agentic-user-token"

        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        client = ApiClient(
            "https://mock.service.url",
            mock_http_client,
            token_provider=TestTokenProvider(),
            agentic_identity=identity,
        )

        clone = client.from_service_url("https://override.service.url")

        assert clone.http is not client.http
        assert clone.http.http is client.http.http
        assert clone._default_agentic_identity is identity

    def test_clone_replaces_http_client_when_agentic_identity_changes(self, mock_http_client):
        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, **_kwargs):
                return "agentic-user-token"

        default_identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="default-app-id",
            agentic_user_id="default-user-id",
            tenant_id="default-tenant-id",
        )
        override_identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="override-app-id",
            agentic_user_id="override-user-id",
            tenant_id="override-tenant-id",
        )
        client = ApiClient(
            "https://mock.service.url",
            mock_http_client,
            token_provider=TestTokenProvider(),
            agentic_identity=default_identity,
        )

        clone = client.for_agentic_identity(override_identity)

        assert clone.http is not client.http
        assert clone.http.http is client.http.http
        assert clone._default_agentic_identity is override_identity

    def test_clone_preserves_agentic_identity_with_explicit_none(self, mock_http_client):
        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        client = ApiClient("https://mock.service.url", mock_http_client, agentic_identity=identity)

        clone = client.clone(agentic_identity=None)

        assert clone._default_agentic_identity is identity

    def test_clone_can_override_service_url_and_clear_agentic_identity(self, mock_http_client):
        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        client = ApiClient("https://mock.service.url", mock_http_client, agentic_identity=identity)

        clone = client.clone(service_url="https://override.service.url/", agentic_identity=AGENTIC_IDENTITY_CLEAR)

        assert clone.service_url == "https://override.service.url"
        assert clone._default_agentic_identity is None

    def test_scoped_helpers_create_expected_clones(self, mock_http_client):
        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        client = ApiClient("https://mock.service.url", mock_http_client)

        service_scoped = client.from_service_url("https://override.service.url/")
        identity_scoped = client.for_agentic_identity(identity)

        assert service_scoped.service_url == "https://override.service.url"
        assert identity_scoped._default_agentic_identity is identity

    @pytest.mark.asyncio
    async def test_clone_uses_scoped_agentic_identity_for_auth(self, request_capture, mock_activity):
        calls = []

        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, *, scope=None, agentic_app_id=None, agentic_user_id=None, tenant_id=None):
                calls.append((scope, agentic_app_id, agentic_user_id, tenant_id))
                return "agentic-user-token"

        default_identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="default-app-id",
            agentic_user_id="default-user-id",
            tenant_id="default-tenant-id",
        )
        override_identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="override-app-id",
            agentic_user_id="override-user-id",
            tenant_id="override-tenant-id",
        )
        client = ApiClient(
            "https://test.service.url",
            request_capture,
            token_provider=TestTokenProvider(),
            agentic_identity=default_identity,
        )

        await client.for_agentic_identity(override_identity).conversations.create_activity(
            "test_conversation_id", mock_activity
        )

        assert calls == [(PUBLIC.agent_bot_scope, "override-app-id", "override-user-id", "override-tenant-id")]
        request = request_capture._capture.last_request
        assert "authorization" in request.headers

    @pytest.mark.asyncio
    async def test_clone_uses_token_for_each_scoped_agentic_identity(self, request_capture, mock_activity):
        calls = []
        identity_1 = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id-1",
            agentic_user_id="agentic-user-id-1",
            tenant_id="tenant-id",
        )
        identity_2 = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id-2",
            agentic_user_id="agentic-user-id-2",
            tenant_id="tenant-id",
        )

        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, *, scope=None, agentic_app_id=None, agentic_user_id=None, tenant_id=None):
                calls.append((scope, agentic_app_id, agentic_user_id, tenant_id))
                if agentic_app_id == identity_1.agentic_app_id:
                    return "token-1"
                if agentic_app_id == identity_2.agentic_app_id:
                    return "token-2"
                return "default-token"

        client = ApiClient(
            "https://test.service.url",
            request_capture,
            token_provider=TestTokenProvider(),
        )

        await client.for_agentic_identity(identity_1).conversations.create_activity(
            "test_conversation_id", mock_activity
        )
        first_request = request_capture._capture.last_request
        await client.for_agentic_identity(identity_2).conversations.create_activity(
            "test_conversation_id", mock_activity
        )
        second_request = request_capture._capture.last_request

        assert calls == [
            (PUBLIC.agent_bot_scope, "agentic-app-id-1", "agentic-user-id-1", "tenant-id"),
            (PUBLIC.agent_bot_scope, "agentic-app-id-2", "agentic-user-id-2", "tenant-id"),
        ]
        assert first_request.headers["authorization"] == "Bearer token-1"
        assert second_request.headers["authorization"] == "Bearer token-2"

    @pytest.mark.asyncio
    async def test_chained_clone_uses_token_for_new_scoped_agentic_identity(self, request_capture, mock_activity):
        calls = []
        identity_1 = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id-1",
            agentic_user_id="agentic-user-id-1",
            tenant_id="tenant-id",
        )
        identity_2 = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id-2",
            agentic_user_id="agentic-user-id-2",
            tenant_id="tenant-id",
        )

        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, *, scope=None, agentic_app_id=None, agentic_user_id=None, tenant_id=None):
                calls.append((scope, agentic_app_id, agentic_user_id, tenant_id))
                if agentic_app_id == identity_1.agentic_app_id:
                    return "token-1"
                if agentic_app_id == identity_2.agentic_app_id:
                    return "token-2"
                return "default-token"

        client = ApiClient(
            "https://test.service.url",
            request_capture,
            token_provider=TestTokenProvider(),
        )

        await (
            client.from_service_url("https://override.service.url")
            .for_agentic_identity(identity_1)
            .conversations.create_activity("test_conversation_id", mock_activity)
        )
        first_request = request_capture._capture.last_request
        await (
            client.for_agentic_identity(identity_1)
            .for_agentic_identity(identity_2)
            .conversations.create_activity("test_conversation_id", mock_activity)
        )
        second_request = request_capture._capture.last_request

        assert calls == [
            (PUBLIC.agent_bot_scope, "agentic-app-id-1", "agentic-user-id-1", "tenant-id"),
            (PUBLIC.agent_bot_scope, "agentic-app-id-2", "agentic-user-id-2", "tenant-id"),
        ]
        assert first_request.headers["authorization"] == "Bearer token-1"
        assert str(first_request.url).startswith("https://override.service.url/")
        assert second_request.headers["authorization"] == "Bearer token-2"
        assert str(second_request.url).startswith("https://test.service.url/")

    @pytest.mark.asyncio
    async def test_clone_none_preserves_scoped_agentic_identity(self, request_capture, mock_activity):
        calls = []

        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, *, scope=None, agentic_app_id=None, agentic_user_id=None, tenant_id=None):
                calls.append((scope, agentic_app_id, agentic_user_id, tenant_id))
                return "bot-token"

        default_identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="default-app-id",
            agentic_user_id="default-user-id",
            tenant_id="default-tenant-id",
        )
        client = ApiClient(
            "https://test.service.url",
            request_capture,
            token_provider=TestTokenProvider(),
            agentic_identity=default_identity,
        )

        await client.clone(agentic_identity=None).conversations.create_activity("test_conversation_id", mock_activity)

        assert calls == [(PUBLIC.agent_bot_scope, "default-app-id", "default-user-id", "default-tenant-id")]

    @pytest.mark.asyncio
    async def test_clone_clear_clears_scoped_agentic_identity(self, request_capture, mock_activity):
        calls = []

        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, *, scope=None, agentic_app_id=None, agentic_user_id=None, tenant_id=None):
                calls.append((scope, agentic_app_id, agentic_user_id, tenant_id))
                return "bot-token"

        default_identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="default-app-id",
            agentic_user_id="default-user-id",
            tenant_id="default-tenant-id",
        )
        client = ApiClient(
            "https://test.service.url",
            request_capture,
            token_provider=TestTokenProvider(),
            agentic_identity=default_identity,
        )

        await client.clone(agentic_identity=AGENTIC_IDENTITY_CLEAR).conversations.create_activity(
            "test_conversation_id", mock_activity
        )

        assert calls == [(PUBLIC.bot_scope, None, None, None)]

    def test_http_client_token_conflicts_with_token_provider(self, request_capture):
        class TestTokenProvider(_TokenProviderAdapter):
            def token(self, **_kwargs):
                return "agentic-user-token"

        request_capture_with_token = request_capture.clone(ClientOptions(token="http-client-token"), share_http=True)

        with pytest.raises(ValueError, match="token provider and an HTTP client token"):
            ApiClient(
                "https://test.service.url",
                request_capture_with_token,
                token_provider=TestTokenProvider(),
                agentic_identity=AgenticIdentity(
                    agentic_app_blueprint_id="blueprint-id",
                    agentic_app_id="agentic-app-id",
                    agentic_user_id="agentic-user-id",
                    tenant_id="tenant-id",
                ),
            )
