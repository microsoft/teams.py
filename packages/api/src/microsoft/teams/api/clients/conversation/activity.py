"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional

from microsoft.teams.common.http import Client

from ...activities import ActivityParams, SentActivity
from ...models import Account
from ..base_client import BaseClient


class ConversationActivityClient(BaseClient):
    """
    Client for managing activities in a Teams conversation.
    """

    def __init__(self, service_url: str, http_client: Optional[Client] = None):
        """
        Initialize the conversation activity client.

        Args:
            service_url: The base URL for the Teams service
            http_client: Optional HTTP client to use. If not provided, a new one will be created.
        """
        super().__init__(http_client)
        self.service_url = service_url

    async def create(self, conversation_id: str, activity: ActivityParams) -> SentActivity:
        """
        Create a new activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity: The activity to create

        Returns:
            The created activity
        """
        response = await self.http.post(
            f"{self.service_url}/v3/conversations/{conversation_id}/activities",
            json=activity.model_dump(by_alias=True, exclude_none=True),
        )

        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def update(self, conversation_id: str, activity_id: str, activity: ActivityParams) -> SentActivity:
        """
        Update an existing activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to update
            activity: The updated activity data

        Returns:
            The updated activity
        """
        response = await self.http.put(
            f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}",
            json=activity.model_dump(by_alias=True),
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def reply(self, conversation_id: str, activity_id: str, activity: ActivityParams) -> SentActivity:
        """
        Reply to an activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to reply to
            activity: The reply activity

        Returns:
            The created reply activity
        """
        activity_json = activity.model_dump(by_alias=True)
        activity_json["replyToId"] = activity_id
        response = await self.http.post(
            f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}",
            json=activity_json,
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def delete(self, conversation_id: str, activity_id: str) -> None:
        """
        Delete an activity from a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to delete
        """
        await self.http.delete(f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}")

    async def get_members(self, conversation_id: str, activity_id: str) -> List[Account]:
        """
        Get the members associated with an activity.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity

        Returns:
            List of Account objects representing the activity members
        """
        response = await self.http.get(
            f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}/members"
        )
        return [Account.model_validate(member) for member in response.json()]
