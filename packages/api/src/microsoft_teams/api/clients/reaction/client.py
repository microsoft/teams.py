"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from microsoft_teams.common.http import Client

from ...models.message import MessageReactionType
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient


class ReactionClient(BaseClient):
    """
    Client for working with app message reactions for a given conversation/activity.
    """

    def __init__(
        self,
        service_url: str,
        http_client: Optional[Client] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ):
        """
        Initialize the reaction client.

        Args:
            service_url: The base URL for the Teams service
            http_client: Optional HTTP client to use. If not provided, a new one will be created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(http_client, api_client_settings)
        self.service_url = service_url

    async def add(
        self,
        conversation_id: str,
        activity_id: str,
        reaction_type: MessageReactionType,
    ) -> None:
        """
        Adds a reaction on an activity in a conversation.

        Args:
            conversation_id: The conversation id.
            activity_id: The id of the activity to react to.
            reaction_type: The reaction type (for example: "like", "heart", "laugh", etc.).
        """
        url = (
            f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        await self.http.put(url)

    async def delete(
        self,
        conversation_id: str,
        activity_id: str,
        reaction_type: MessageReactionType,
    ) -> None:
        """
        Removes a reaction from an activity in a conversation.

        Args:
            conversation_id: The conversation id.
            activity_id: The id of the activity the reaction is on.
            reaction_type: The reaction type to remove (for example: "like", "heart", "laugh", etc.).
        """
        url = (
            f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/reactions/{reaction_type}"
        )
        await self.http.delete(url)
