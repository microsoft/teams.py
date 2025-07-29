"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
#

import pytest
from microsoft.teams.api.clients.team import TeamClient
from microsoft.teams.api.models import ChannelInfo, TeamDetails
from microsoft.teams.common.http import Client, ClientOptions


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

    def test_http_client_property(self, mock_http_client):
        """Test HTTP client property getter and setter."""
        service_url = "https://test.service.url"
        client = TeamClient(service_url, mock_http_client)

        assert client.http == mock_http_client

        # Test setter
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))
        client.http = new_http_client

        assert client.http == new_http_client
