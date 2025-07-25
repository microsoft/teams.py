"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional, Union

from microsoft.teams.common.http import Client
from pydantic import Field
from typing_extensions import Annotated

from ...activities.command import CommandResultActivityInput, CommandSendActivityInput
from ...activities.conversation import ConversationUpdateActivityInput, EndOfConversationActivityInput
from ...activities.event import (
    MeetingEndEventActivityInput,
    MeetingParticipantJoinEventActivityInput,
    MeetingParticipantLeaveEventActivityInput,
    MeetingStartEventActivityInput,
    ReadReceiptEventActivityInput,
)
from ...activities.handoff import HandoffActivityInput
from ...activities.install_update import InstalledActivityInput, UninstalledActivityInput
from ...activities.invoke import AdaptiveCardInvokeActivity
from ...activities.invoke.config import ConfigFetchInvokeActivityInput, ConfigSubmitInvokeActivityInput
from ...activities.invoke.execute_action import ExecuteActionInvokeActivityInput
from ...activities.invoke.file_consent import FileConsentInvokeActivityInput
from ...activities.invoke.handoff_action import HandoffActionInvokeActivityInput
from ...activities.invoke.message.submit_action import MessageSubmitActionInvokeActivityInput
from ...activities.invoke.sign_in.token_exchange import SignInTokenExchangeInvokeActivityInput
from ...activities.invoke.sign_in.verify_state import SignInVerifyStateInvokeActivityInput
from ...activities.invoke.tab.tab_fetch import TabFetchInvokeActivityInput
from ...activities.invoke.tab.tab_submit import TabSubmitInvokeActivityInput
from ...activities.invoke.task.task_fetch import TaskFetchInvokeActivityInput
from ...activities.invoke.task.task_submit import TaskSubmitInvokeActivityInput
from ...activities.message import (
    MessageActivityInput,
    MessageDeleteActivityInput,
    MessageReactionActivityInput,
    MessageUpdateActivityInput,
)
from ...activities.trace import TraceActivityInput
from ...activities.typing import TypingActivityInput
from ...models import Account, Resource
from ..base_client import BaseClient

# Union of all activity input types (each defined next to their respective activities)
ActivityParams = Annotated[
    Union[
        # Simple activities
        ConversationUpdateActivityInput,
        EndOfConversationActivityInput,
        HandoffActivityInput,
        TraceActivityInput,
        TypingActivityInput,
        # Message activities
        MessageActivityInput,
        MessageDeleteActivityInput,
        MessageReactionActivityInput,
        MessageUpdateActivityInput,
        # Command activities
        CommandSendActivityInput,
        CommandResultActivityInput,
        # Event activities
        ReadReceiptEventActivityInput,
        MeetingStartEventActivityInput,
        MeetingEndEventActivityInput,
        MeetingParticipantJoinEventActivityInput,
        MeetingParticipantLeaveEventActivityInput,
        # Install/Update activities
        InstalledActivityInput,
        UninstalledActivityInput,
        # Invoke activities
        AdaptiveCardInvokeActivity,
        ConfigFetchInvokeActivityInput,
        ConfigSubmitInvokeActivityInput,
        ExecuteActionInvokeActivityInput,
        FileConsentInvokeActivityInput,
        HandoffActionInvokeActivityInput,
        MessageSubmitActionInvokeActivityInput,
        SignInTokenExchangeInvokeActivityInput,
        SignInVerifyStateInvokeActivityInput,
        TabFetchInvokeActivityInput,
        TabSubmitInvokeActivityInput,
        TaskFetchInvokeActivityInput,
        TaskSubmitInvokeActivityInput,
    ],
    Field(discriminator="type"),
]


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

    async def create(self, conversation_id: str, activity: ActivityParams) -> Resource:
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
            json=activity.model_dump(by_alias=True),
        )
        return Resource(**response.json())

    async def update(self, conversation_id: str, activity_id: str, activity: ActivityParams) -> Resource:
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
        return Resource(**response.json())

    async def reply(self, conversation_id: str, activity_id: str, activity: ActivityParams) -> Resource:
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
        return Resource(**response.json())

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
