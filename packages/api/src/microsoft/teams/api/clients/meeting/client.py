"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

from ...models import MeetingInfo, MeetingParticipant
from ..base_client import BaseClient


class MeetingClient(BaseClient):
    """Client for managing Teams meetings."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
    ) -> None:
        """
        Initialize the MeetingClient.

        Args:
            service_url: The service URL for API calls.
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
        """
        super().__init__(options)
        self.service_url = service_url

    async def get_by_id(self, id: str) -> MeetingInfo:
        """
        Get meeting information by ID.

        Args:
            id: The meeting ID.

        Returns:
            The meeting information.
        """
        response = await self.http.get(f"{self.service_url}/v1/meetings/{id}")
        return MeetingInfo.model_validate(response.json())

    async def get_participant(self, meeting_id: str, id: str) -> MeetingParticipant:
        """
        Get meeting participant information.

        Args:
            meeting_id: The meeting ID.
            id: The participant ID.

        Returns:
            The meeting participant information.
        """
        response = await self.http.get(f"{self.service_url}/v1/meetings/{meeting_id}/participants/{id}")
        return MeetingParticipant.model_validate(response.json())
