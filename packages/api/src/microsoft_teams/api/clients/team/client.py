"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import List, Optional, Union

from microsoft_teams.common.http import Client, ClientOptions

from ...models import AgenticIdentity, ChannelInfo, TeamDetails
from .._auth_provider_interceptor import AGENTIC_IDENTITY_EXTENSION
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient
from .params import GetTeamConversationsResponse


class TeamClient(BaseClient):
    """Client for managing Teams teams."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """
        Initialize the TeamClient.

        Args:
            service_url: The service URL for API calls.
            options: Optional Client or ClientOptions instance. If not provided, a default Client will be created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(options, api_client_settings)
        self.service_url = service_url.rstrip("/")

    async def get_by_id(
        self, id: str, *, service_url: str | None = None, agentic_identity: AgenticIdentity | None = None
    ) -> TeamDetails:
        """
        Get team details by ID.

        Args:
            id: The team ID.

        Returns:
            The team details.
        """
        response = await self.http.get(
            f"{self._get_service_url(service_url)}/v3/teams/{id}",
            extensions={AGENTIC_IDENTITY_EXTENSION: agentic_identity},
        )
        return TeamDetails.model_validate(response.json())

    async def get_conversations(
        self, id: str, *, service_url: str | None = None, agentic_identity: AgenticIdentity | None = None
    ) -> List[ChannelInfo]:
        """
        Get team conversations (channels).

        Args:
            id: The team ID.

        Returns:
            List of channel information.
        """
        response = await self.http.get(
            f"{self._get_service_url(service_url)}/v3/teams/{id}/conversations",
            extensions={AGENTIC_IDENTITY_EXTENSION: agentic_identity},
        )
        return GetTeamConversationsResponse.model_validate(response.json()).conversations
