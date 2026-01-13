"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Optional

from microsoft_teams.common.http import Client

from ...activities import ActivityParams, SentActivity
from ...models import Account
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient


class ConversationActivityClient(BaseClient):
    """
    Client for managing activities in a Teams conversation.
    """

    def __init__(
        self,
        service_url: str,
        http_client: Optional[Client] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ):
        """
        Initialize the conversation activity client.

        Args:
            service_url: The base URL for the Teams service
            http_client: Optional HTTP client to use. If not provided, a new one will be created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(http_client, api_client_settings)
        self.service_url = service_url

    async def create(
        self, conversation_id: str, activity: ActivityParams, *, is_targeted: bool = False
    ) -> SentActivity:
        """
        Create a new activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity: The activity to create
            is_targeted: When True, sends the message privately to the recipient specified in activity.recipient

        Returns:
            The created activity
        """
        url = f"{self.service_url}/v3/conversations/{conversation_id}/activities"
        params: dict[str, Any] = {}
        if is_targeted:
            params["isTargetedActivity"] = "true"

        response = await self.http.post(
            url,
            json=activity.model_dump(by_alias=True, exclude_none=True),
            params=params or None,
        )

        # Note: Typing activities (non-streaming) always produce empty responses.
        # Note: For streaming activities, the first response includes the stream id.
        # Note: Subsequent responses for streaming activities are empty (both typing and message type).
        id = response.json().get("id", "DO_NOT_USE_PLACEHOLDER_ID")
        return SentActivity(id=id, activity_params=activity)

    async def update(
        self, conversation_id: str, activity_id: str, activity: ActivityParams, *, is_targeted: bool = False
    ) -> SentActivity:
        """
        Update an existing activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to update
            activity: The updated activity data
            is_targeted: When True, sends the message privately to the recipient specified in activity.recipient

        Returns:
            The updated activity
        """
        url = f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}"
        params: dict[str, Any] = {}
        if is_targeted:
            params["isTargetedActivity"] = "true"

        response = await self.http.put(
            url,
            json=activity.model_dump(by_alias=True),
            params=params or None,
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def reply(
        self, conversation_id: str, activity_id: str, activity: ActivityParams, *, is_targeted: bool = False
    ) -> SentActivity:
        """
        Reply to an activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to reply to
            activity: The reply activity
            is_targeted: When True, sends the message privately to the recipient specified in activity.recipient

        Returns:
            The created reply activity
        """
        activity_json = activity.model_dump(by_alias=True)
        activity_json["replyToId"] = activity_id

        url = f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}"
        params: dict[str, Any] = {}
        if is_targeted:
            params["isTargetedActivity"] = "true"

        response = await self.http.post(
            url,
            json=activity_json,
            params=params or None,
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def delete(self, conversation_id: str, activity_id: str, *, is_targeted: bool = False) -> None:
        """
        Delete an activity from a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to delete
            is_targeted: When True, deletes a targeted message privately
        """
        url = f"{self.service_url}/v3/conversations/{conversation_id}/activities/{activity_id}"
        params: dict[str, Any] = {}
        if is_targeted:
            params["isTargetedActivity"] = "true"

        await self.http.delete(url, params=params or None)

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
