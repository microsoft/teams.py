"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft_teams.common.http import Client, ClientOptions

from ...models import MeetingInfo, MeetingParticipant
from ...models.meetings.meeting_notification import MeetingNotificationParams, MeetingNotificationResponse
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient


class MeetingClient(BaseClient):
    """Client for managing Teams meetings."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """
        Initialize the MeetingClient.

        Args:
            service_url: The service URL for API calls.
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(options, api_client_settings)
        self.service_url = service_url.rstrip("/")

    async def get_by_id(self, id: str) -> MeetingInfo:
        """
        Retrieves meeting information including details, organizer, and conversation.

        Args:
            id: The meeting ID.

        Returns:
            The meeting information.
        """
        response = await self.http.get(f"{self.service_url}/v1/meetings/{id}")
        return MeetingInfo.model_validate(response.json())

    async def get_participant(self, meeting_id: str, id: str, tenant_id: str) -> MeetingParticipant:
        """
        Retrieves information about a specific participant in a meeting.

        Args:
            meeting_id: The meeting ID.
            id: The user AAD object ID.
            tenant_id: The tenant ID of the meeting and user.

        Returns:
            MeetingParticipant: The meeting participant information.
        """
        url = f"{self.service_url}/v1/meetings/{meeting_id}/participants/{id}?tenantId={tenant_id}"
        response = await self.http.get(url)
        return MeetingParticipant.model_validate(response.json())

    async def send_notification(
        self, meeting_id: str, params: MeetingNotificationParams
    ) -> Optional[MeetingNotificationResponse]:
        """
        Send a targeted meeting notification to participants.

        Returns None on full success (HTTP 202). Returns a MeetingNotificationResponse
        with failure details on partial success (HTTP 207).

        Args:
            meeting_id: The BASE64-encoded meeting ID.
            params: The notification parameters including recipients and surfaces.

        Returns:
            None if all notifications were sent successfully, or a MeetingNotificationResponse
            with per-recipient failure details on partial success.
        """
        response = await self.http.post(
            f"{self.service_url}/v1/meetings/{meeting_id}/notification",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )
        if not response.text:
            return None
        return MeetingNotificationResponse.model_validate(response.json())
