"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Optional, Type

from microsoft.teams.common.http import Client
from pydantic import create_model
from pydantic_core import PydanticUndefinedType

from ...activities import ActivityBase
from ...models import Account, CustomBaseModel
from ..base_client import BaseClient


def partial_model(model: Type[CustomBaseModel]) -> Type[CustomBaseModel]:
    """
    Creates a partial model, making all fields optional
    except for the 'type' field.
    """
    base_fields = set(ActivityBase.model_fields.keys())
    curr_fields = model.model_fields.items()
    fields: dict[str, Any] = {}

    for field_name, field_info in curr_fields:
        # Only make ActivityBase fields optional (except 'type')
        if field_name in base_fields and field_name != "type":
            annotation = Optional[field_info.annotation]  # type: ignore
            default = None if isinstance(field_info.default, PydanticUndefinedType) else field_info.default
            fields[field_name] = (annotation, default)
        else:
            fields[field_name] = (field_info.annotation, field_info.default)

    return create_model(
        f"Partial{model.__name__}",
        __base__=model,
        __module__=model.__module__,
        **{k: v for k, v in fields.items()},
    )


@partial_model
class ActivityParams(ActivityBase):
    pass


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

    async def create(self, conversation_id: str, activity: ActivityParams) -> ActivityParams:
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
        return ActivityParams(value={**response.json()})

    async def update(self, conversation_id: str, activity_id: str, activity: ActivityParams) -> ActivityParams:
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
        return ActivityParams(value={**response.json()})

    async def reply(self, conversation_id: str, activity_id: str, activity: ActivityParams) -> ActivityParams:
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
        return ActivityParams(value={**response.json()})

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
