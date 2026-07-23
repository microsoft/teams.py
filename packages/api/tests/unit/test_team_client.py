"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from microsoft_teams.api.clients import ApiClient
from microsoft_teams.api.clients.team import TeamClient
from microsoft_teams.api.models import AgenticUser, ChannelInfo, TeamDetails
from microsoft_teams.common.http import Client, ClientOptions


@pytest.mark.unit
class TestTeamClient:
    """Unit tests for TeamClient."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_http_client):
        """Test getting team by ID."""
        service_url = "https://test.service.url"
        client = TeamClient(service_url, mock_http_client)
        team_id = "test_team_id"

        result = await client.get_by_id(team_id)

        assert isinstance(result, TeamDetails)

    @pytest.mark.asyncio
    async def test_get_conversations(self, mock_http_client):
        """Test getting team conversations."""
        service_url = "https://test.service.url"
        client = TeamClient(service_url, mock_http_client)
        team_id = "test_team_id"

        result = await client.get_conversations(team_id)

        assert isinstance(result, list)
        assert all(isinstance(channel, ChannelInfo) for channel in result)

    @pytest.mark.asyncio
    async def test_team_operations_use_scoped_service_url(self, mock_http_client):
        client = (
            ApiClient("https://test.service.url", mock_http_client)
            .from_service_url("https://override.service.url/")
            .teams
        )

        team_response = httpx.Response(
            200,
            json={"id": "team-id", "name": "Team"},
            headers={"content-type": "application/json"},
        )
        with patch.object(client.http, "get", new_callable=AsyncMock, return_value=team_response) as mock_get:
            await client.get_by_id("team-id")

        mock_get.assert_called_once_with("https://override.service.url/v3/teams/team-id")

        conversations_response = httpx.Response(
            200,
            json={"conversations": []},
            headers={"content-type": "application/json"},
        )
        with patch.object(
            client.http, "get", new_callable=AsyncMock, return_value=conversations_response
        ) as mock_get_conversations:
            await client.get_conversations("team-id")

        mock_get_conversations.assert_called_once_with(
            "https://override.service.url/v3/teams/team-id/conversations",
        )

    @pytest.mark.asyncio
    async def test_get_by_id_uses_auth_provider_for_bot_token(self, mock_http_client):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", mock_http_client, auth_provider=TestAuthProvider()).teams
        await client.get_by_id("team-id")

        assert calls == [(None, None)]

    @pytest.mark.asyncio
    async def test_get_conversations_uses_agentic_user(self, mock_http_client):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "agentic-user-token"

        identity = AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url", mock_http_client, auth_provider=TestAuthProvider(), agentic_user=identity
        ).teams
        await client.get_conversations("team-id")

        assert calls == [(None, identity)]

    def test_http_client_property(self, mock_http_client):
        """Test HTTP client property getter and setter."""
        service_url = "https://test.service.url"
        client = TeamClient(service_url, mock_http_client)

        assert client.http == mock_http_client

        # Test setter
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))
        client.http = new_http_client

        assert client.http == new_http_client

    def test_team_client_strips_trailing_slash(self, mock_http_client):
        """Test TeamClient strips trailing slash from service_url."""
        service_url = "https://test.service.url/"
        client = TeamClient(service_url, mock_http_client)

        assert client.service_url == "https://test.service.url"
