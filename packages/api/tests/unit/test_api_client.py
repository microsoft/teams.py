"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import pytest
from microsoft_teams.api.clients import AGENTIC_IDENTITY_OMIT, ApiClient, ReactionClient
from microsoft_teams.api.clients._auth_provider_interceptor import AuthProviderInterceptor
from microsoft_teams.api.models import AgenticIdentity
from microsoft_teams.common.http import Client, ClientOptions


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

    def test_reactions_inherits_agentic_auth_defaults(self, mock_http_client):
        """Test reactions inherits agentic auth defaults from ApiClient."""
        auth_provider = object()
        identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://mock.service.url",
            mock_http_client,
            auth_provider=auth_provider,
            agentic_identity=identity,
        )

        reactions = client.reactions

        assert not hasattr(reactions, "_auth_provider")
        assert not hasattr(reactions, "_agentic_identity")
        interceptor = next(
            interceptor
            for interceptor in mock_http_client.interceptors
            if isinstance(interceptor, AuthProviderInterceptor)
        )
        assert interceptor._default_agentic_identity is identity

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
        identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient("https://mock.service.url", mock_http_client, agentic_identity=identity)

        clone = client.clone()

        assert clone.service_url == "https://mock.service.url"
        assert clone._default_agentic_identity is identity
        assert clone._api_client_settings is client._api_client_settings
        assert clone._cloud is client._cloud

    def test_clone_can_override_service_url_and_clear_agentic_identity(self, mock_http_client):
        identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient("https://mock.service.url", mock_http_client, agentic_identity=identity)

        clone = client.clone(service_url="https://override.service.url/", agentic_identity=None)

        assert clone.service_url == "https://override.service.url"
        assert clone._default_agentic_identity is None

    def test_clone_omit_clears_agentic_identity(self, mock_http_client):
        identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient("https://mock.service.url", mock_http_client, agentic_identity=identity)

        clone = client.clone(agentic_identity=AGENTIC_IDENTITY_OMIT)

        assert clone._default_agentic_identity is None

    def test_scoped_helpers_create_expected_clones(self, mock_http_client):
        identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient("https://mock.service.url", mock_http_client)

        service_scoped = client.from_service_url("https://override.service.url/")
        identity_scoped = client.from_agentic_identity(identity)
        alias_scoped = client.for_agentic_identity(identity)

        assert service_scoped.service_url == "https://override.service.url"
        assert identity_scoped._default_agentic_identity is identity
        assert alias_scoped._default_agentic_identity is identity

    @pytest.mark.asyncio
    async def test_clone_uses_scoped_agentic_identity_for_auth(self, request_capture, mock_activity):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_identity=None):
                calls.append((scope, agentic_identity))
                return "agentic-token"

        default_identity = AgenticIdentity("default-app-id", "default-user-id", tenant_id="default-tenant-id")
        override_identity = AgenticIdentity("override-app-id", "override-user-id", tenant_id="override-tenant-id")
        client = ApiClient(
            "https://test.service.url",
            request_capture,
            auth_provider=TestAuthProvider(),
            agentic_identity=default_identity,
        )

        await client.from_agentic_identity(override_identity).conversations.create_activity(
            "test_conversation_id", mock_activity
        )

        assert calls == [(None, override_identity)]
        request = request_capture._capture.last_request
        assert "authorization" in request.headers

    @pytest.mark.asyncio
    async def test_clone_none_clears_scoped_agentic_identity(self, request_capture, mock_activity):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_identity=None):
                calls.append((scope, agentic_identity))
                return "bot-token"

        default_identity = AgenticIdentity("default-app-id", "default-user-id", tenant_id="default-tenant-id")
        client = ApiClient(
            "https://test.service.url",
            request_capture,
            auth_provider=TestAuthProvider(),
            agentic_identity=default_identity,
        )

        await client.clone(agentic_identity=None).conversations.create_activity("test_conversation_id", mock_activity)

        assert calls == [(None, None)]
