"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import pytest
from microsoft_teams.api.auth.cloud_environment import PUBLIC, with_overrides
from microsoft_teams.api.clients import ApiClient
from microsoft_teams.api.clients.reaction import ReactionClient
from microsoft_teams.api.models import AgenticUser


@pytest.mark.unit
class TestReactionClient:
    """Unit tests for ReactionClient."""

    def test_reaction_client_initialization(self, mock_http_client):
        """Test ReactionClient initialization."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        assert client.http == mock_http_client
        assert client.service_url == service_url

    def test_reaction_client_strips_trailing_slash(self, mock_http_client):
        """Test ReactionClient strips trailing slash from service_url."""
        service_url = "https://test.service.url/"
        client = ReactionClient(service_url, mock_http_client)

        assert client.service_url == "https://test.service.url"

    def test_reaction_client_initialization_with_options(self):
        """Test ReactionClient initialization with ClientOptions."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url)

        assert client.http is not None
        assert client.service_url == service_url

    @pytest.mark.asyncio
    async def test_add_reaction(self, mock_http_client):
        """Test adding a reaction to an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "like"

        with patch.object(mock_http_client, "put", new_callable=AsyncMock) as mock_put:
            await client.add(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_put.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_reaction_operations_use_scoped_service_url(self, mock_http_client):
        client = ReactionClient("https://override.service.url/", mock_http_client)

        with patch.object(mock_http_client, "put", new_callable=AsyncMock) as mock_put:
            await client.add("test_conversation_id", "test_activity_id", "like")

        mock_put.assert_called_once_with(
            "https://override.service.url/v3/conversations/test_conversation_id/activities/test_activity_id/reactions/like",
        )

        with patch.object(mock_http_client, "delete", new_callable=AsyncMock) as mock_delete:
            await client.delete("test_conversation_id", "test_activity_id", "like")

        mock_delete.assert_called_once_with(
            "https://override.service.url/v3/conversations/test_conversation_id/activities/test_activity_id/reactions/like",
        )

    @pytest.mark.asyncio
    async def test_add_reaction_uses_agentic_user(self, mock_http_client):
        """Test adding a reaction with an agentic user token."""
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "agentic-user-token"

        cloud = with_overrides(PUBLIC, agent_bot_scope="agentic-user-scope")
        identity = AgenticUser("agent-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url",
            mock_http_client,
            auth_provider=TestAuthProvider(),
            agentic_user=identity,
            cloud=cloud,
        ).reactions

        await client.add("test_conversation_id", "test_activity_id", "like")

        assert calls == [(None, identity)]

    @pytest.mark.asyncio
    async def test_add_reaction_uses_auth_provider_for_bot_token(self, mock_http_client):
        """Test adding a reaction with an auth provider but no agentic user."""
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", mock_http_client, auth_provider=TestAuthProvider()).reactions

        await client.add("test_conversation_id", "test_activity_id", "like")

        assert calls == [(None, None)]

    @pytest.mark.asyncio
    async def test_add_heart_reaction(self, mock_http_client):
        """Test adding a heart reaction to an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "heart"

        with patch.object(mock_http_client, "put", new_callable=AsyncMock) as mock_put:
            await client.add(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_put.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_delete_reaction(self, mock_http_client):
        """Test removing a reaction from an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "like"

        with patch.object(mock_http_client, "delete", new_callable=AsyncMock) as mock_delete:
            await client.delete(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_delete.assert_called_once_with(expected_url)

    @pytest.mark.asyncio
    async def test_delete_reaction_uses_scoped_agentic_user(self, mock_http_client):
        """Test removing a reaction with a scoped agentic user token."""
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "agentic-user-token"

        identity = AgenticUser("agent-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url", mock_http_client, auth_provider=TestAuthProvider(), agentic_user=identity
        ).reactions

        await client.delete("test_conversation_id", "test_activity_id", "like")

        assert calls == [(None, identity)]

    @pytest.mark.asyncio
    async def test_delete_laugh_reaction(self, mock_http_client):
        """Test removing a laugh reaction from an activity."""
        service_url = "https://test.service.url"
        client = ReactionClient(service_url, mock_http_client)

        conversation_id = "test_conversation_id"
        activity_id = "test_activity_id"
        reaction_type = "laugh"

        with patch.object(mock_http_client, "delete", new_callable=AsyncMock) as mock_delete:
            await client.delete(conversation_id, activity_id, reaction_type)

        expected_url = (
            f"{service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        mock_delete.assert_called_once_with(expected_url)
