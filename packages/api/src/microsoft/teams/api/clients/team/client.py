"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

from ...models import ChannelInfo, TeamDetails
from ..base_client import BaseClient


class TeamClient(BaseClient):
    """Client for managing Teams teams."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
    ) -> None:
        """
        Initialize the TeamClient.

        Args:
            service_url: The service URL for API calls.
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
        """
        super().__init__(options)
        self.service_url = service_url

    async def get_by_id(self, id: str) -> TeamDetails:
        """
        Get team details by ID.

        Args:
            id: The team ID.

        Returns:
            The team details.
        """
        response = await self.http.get(f"{self.service_url}/v3/teams/{id}")
        return TeamDetails.model_validate(response.json())

    async def get_conversations(self, id: str) -> List[ChannelInfo]:
        """
        Get team conversations (channels).

        Args:
            id: The team ID.

        Returns:
            List of channel information.
        """
        response = await self.http.get(f"{self.service_url}/v3/teams/{id}/conversations")
        return [ChannelInfo.model_validate(channel) for channel in response.json()]
