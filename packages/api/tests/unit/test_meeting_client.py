"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft.teams.api.clients.meeting import MeetingClient
from microsoft.teams.api.models import MeetingInfo, MeetingParticipant
from microsoft.teams.common.http import Client, ClientOptions


@pytest.mark.unit
class TestMeetingClient:
    """Unit tests for MeetingClient."""

    @pytest.mark.asyncio
    async def test_get_by_id(self, mock_http_client):
        """Test getting meeting by ID."""
        service_url = "https://test.service.url"
        client = MeetingClient(service_url, mock_http_client)
        meeting_id = "test_meeting_id"

        result = await client.get_by_id(meeting_id)

        assert isinstance(result, MeetingInfo)

    @pytest.mark.asyncio
    async def test_get_participant(self, mock_http_client):
        """Test getting meeting participant."""
        service_url = "https://test.service.url"
        client = MeetingClient(service_url, mock_http_client)
        meeting_id = "test_meeting_id"
        participant_id = "test_participant_id"

        result = await client.get_participant(meeting_id, participant_id)

        assert isinstance(result, MeetingParticipant)

    def test_http_client_property(self, mock_http_client):
        """Test HTTP client property getter and setter."""
        service_url = "https://test.service.url"
        client = MeetingClient(service_url, mock_http_client)

        assert client.http == mock_http_client

        # Test setter
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))
        client.http = new_http_client

        assert client.http == new_http_client
