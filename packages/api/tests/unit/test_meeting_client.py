"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, patch

import httpx
import pytest
from microsoft_teams.api.clients import ApiClient
from microsoft_teams.api.clients.meeting import MeetingClient
from microsoft_teams.api.models import (
    AgenticUser,
    MeetingInfo,
    MeetingNotificationParams,
    MeetingNotificationResponse,
    MeetingNotificationSurface,
    MeetingNotificationValue,
    MeetingParticipant,
)
from microsoft_teams.common.http import Client, ClientOptions


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
        tenant_id = "tenant-id"

        result = await client.get_participant(meeting_id, participant_id, tenant_id)

        assert isinstance(result, MeetingParticipant)

    @pytest.mark.asyncio
    async def test_meeting_operations_use_scoped_service_url(self, mock_http_client):
        client = (
            ApiClient("https://test.service.url", mock_http_client)
            .from_service_url("https://override.service.url/")
            .meetings
        )

        meeting_response = httpx.Response(
            200,
            json={
                "id": "meeting-id",
                "details": {
                    "id": "meeting-id",
                    "type": "meetingChat",
                    "joinUrl": "https://teams.microsoft.com/l/meetup-join/meeting-id",
                    "title": "Meeting",
                    "msGraphResourceId": "graph-resource-id",
                },
            },
            headers={"content-type": "application/json"},
        )
        with patch.object(client.http, "get", new_callable=AsyncMock, return_value=meeting_response) as mock_get:
            await client.get_by_id("meeting-id")

        mock_get.assert_called_once_with("https://override.service.url/v1/meetings/meeting-id")

        participant_response = httpx.Response(
            200,
            json={"user": {"id": "participant-id"}},
            headers={"content-type": "application/json"},
        )
        with patch.object(
            client.http, "get", new_callable=AsyncMock, return_value=participant_response
        ) as mock_get_participant:
            await client.get_participant("meeting-id", "participant-id", "tenant-id")

        mock_get_participant.assert_called_once_with(
            "https://override.service.url/v1/meetings/meeting-id/participants/participant-id?tenantId=tenant-id",
        )

        params = MeetingNotificationParams(
            value=MeetingNotificationValue(
                recipients=["mock_aad_oid"],
                surfaces=[MeetingNotificationSurface(surface="meetingTabIcon", tab_entity_id="test")],
            )
        )
        notification_response = httpx.Response(202, content=b"", headers={"content-type": "application/json"})
        with patch.object(client.http, "post", new_callable=AsyncMock, return_value=notification_response) as mock_post:
            await client.send_notification("meeting-id", params)

        mock_post.assert_called_once_with(
            "https://override.service.url/v1/meetings/meeting-id/notification",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )

    @pytest.mark.asyncio
    async def test_get_by_id_uses_auth_provider_for_bot_token(self, mock_http_client):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "bot-token"

        client = ApiClient("https://test.service.url", mock_http_client, auth_provider=TestAuthProvider()).meetings
        await client.get_by_id("meeting-id")

        assert calls == [(None, None)]

    @pytest.mark.asyncio
    async def test_get_participant_uses_agentic_user(self, mock_http_client):
        calls = []

        class TestAuthProvider:
            def token(self, *, scope=None, agentic_user=None):
                calls.append((scope, agentic_user))
                return "agentic-user-token"

        identity = AgenticUser("agentic-app-instance-id", "agentic-user-id", tenant_id="tenant-id")
        client = ApiClient(
            "https://test.service.url", mock_http_client, auth_provider=TestAuthProvider(), agentic_user=identity
        ).meetings
        await client.get_participant("meeting-id", "participant-id", "tenant-id")

        assert calls == [(None, identity)]

    def test_http_client_property(self, mock_http_client):
        """Test HTTP client property getter and setter."""
        service_url = "https://test.service.url"
        client = MeetingClient(service_url, mock_http_client)

        assert client.http == mock_http_client

        # Test setter
        new_http_client = Client(ClientOptions(base_url="https://new.api.com"))
        client.http = new_http_client

        assert client.http == new_http_client

    def test_meeting_client_strips_trailing_slash(self, mock_http_client):
        """Test MeetingClient strips trailing slash from service_url."""
        service_url = "https://test.service.url/"
        client = MeetingClient(service_url, mock_http_client)

        assert client.service_url == "https://test.service.url"

    @pytest.mark.asyncio
    async def test_send_notification_partial_failure(self, mock_http_client):
        """Test send_notification returns MeetingNotificationResponse on partial failure (HTTP 207)."""

        service_url = "https://test.service.url"
        client = MeetingClient(service_url, mock_http_client)

        params = MeetingNotificationParams(
            value=MeetingNotificationValue(
                recipients=["mock_aad_oid"],
                surfaces=[MeetingNotificationSurface(surface="meetingTabIcon", tab_entity_id="test")],
            )
        )

        partial_failure_response = httpx.Response(
            207,
            json={
                "recipientsFailureInfo": [
                    {
                        "recipientMri": "8:orgid:mock_recipient",
                        "errorCode": "BadArgument",
                        "failureReason": "Invalid recipient",
                    }
                ]
            },
            headers={"content-type": "application/json"},
        )
        with patch.object(mock_http_client, "post", new_callable=AsyncMock, return_value=partial_failure_response):
            result = await client.send_notification("mock_meeting_id", params)

        assert isinstance(result, MeetingNotificationResponse)
        assert result.recipients_failure_info is not None
        assert len(result.recipients_failure_info) == 1
        assert result.recipients_failure_info[0].error_code == "BadArgument"

    @pytest.mark.asyncio
    async def test_send_notification_full_success(self, mock_http_client):
        """Test send_notification returns None on full success (HTTP 202, empty body)."""
        import httpx

        service_url = "https://test.service.url"
        client = MeetingClient(service_url, mock_http_client)

        params = MeetingNotificationParams(
            value=MeetingNotificationValue(
                recipients=["mock_aad_oid"],
                surfaces=[MeetingNotificationSurface(surface="meetingTabIcon", tab_entity_id="test")],
            )
        )

        empty_response = httpx.Response(202, content=b"", headers={"content-type": "application/json"})
        with patch.object(mock_http_client, "post", new_callable=AsyncMock, return_value=empty_response):
            result = await client.send_notification("mock_meeting_id", params)

        assert result is None
