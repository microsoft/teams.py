"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Optional, cast

import httpx
from microsoft_teams.common.experimental import experimental
from microsoft_teams.common.http import Client
from opentelemetry.trace import Span

from ...activities import ActivityParams, SentActivity
from ...diagnostics._constants import (
    API_ATTRIBUTE_NAMES,
    API_OUTBOUND_OPERATIONS,
)
from ...diagnostics._outbound import ApiOutboundResponseHook, ApiOutboundTelemetryMetadata
from ...models import TeamsChannelAccount
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient

_PLACEHOLDER_ACTIVITY_ID = "DO_NOT_USE_PLACEHOLDER_ID"


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
        self.service_url = service_url.rstrip("/")

    async def create(
        self,
        conversation_id: str,
        activity: ActivityParams,
    ) -> SentActivity:
        """
        Create a new activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity: The activity to create

        Returns:
            The created activity
        """

        # TODO: Will be deprecated alongside accessor in ConversationClient
        response = await self.http.post(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities",
            json=activity.model_dump(by_alias=True, exclude_none=True),
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.create,
                conversation_id,
                activity=activity,
                on_response=_set_response_activity_id,
            ),
        )

        # Note: Typing activities (non-streaming) always produce empty responses.
        # Note: For streaming activities, the first response includes the stream id.
        # Note: Subsequent responses for streaming activities are empty (both typing and message type).
        response_body = response.json()
        id = response_body.get("id", _PLACEHOLDER_ACTIVITY_ID)
        return SentActivity(id=id, activity_params=activity)

    async def update(
        self,
        conversation_id: str,
        activity_id: str,
        activity: ActivityParams,
    ) -> SentActivity:
        """
        Update an existing activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to update
            activity: The updated activity data

        Returns:
            The updated activity
        """
        # TODO: Will be deprecated alongside accessor in ConversationClient
        response = await self.http.put(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities/{activity_id}",
            json=activity.model_dump(by_alias=True, exclude_none=True),
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.update,
                conversation_id,
                activity=activity,
                activity_id=activity_id,
                on_response=_set_response_activity_id,
            ),
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def reply(
        self,
        conversation_id: str,
        activity_id: str,
        activity: ActivityParams,
    ) -> SentActivity:
        """
        Reply to an activity in a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to reply to
            activity: The reply activity

        Returns:
            The created reply activity
        """
        # TODO: Will be deprecated alongside accessor in ConversationClient
        activity_json = activity.model_dump(by_alias=True, exclude_none=True)
        activity_json["replyToId"] = activity_id
        response = await self.http.post(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities/{activity_id}",
            json=activity_json,
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.reply,
                conversation_id,
                activity=activity,
                activity_id=activity_id,
                on_response=_set_response_activity_id,
            ),
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    async def delete(
        self,
        conversation_id: str,
        activity_id: str,
    ) -> None:
        """
        Delete an activity from a conversation.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to delete
        """
        await self.http.delete(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities/{activity_id}",
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.delete,
                conversation_id,
                activity_id=activity_id,
            ),
        )

    async def get_members(
        self,
        conversation_id: str,
        activity_id: str,
    ) -> List[TeamsChannelAccount]:
        """
        Get the members associated with an activity.

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity

        Returns:
            List of TeamsChannelAccount objects representing the activity members
        """
        # TODO: Will be deprecated alongside accessor in ConversationClient
        response = await self.http.get(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities/{activity_id}/members",
        )
        return [TeamsChannelAccount.model_validate(member) for member in response.json()]

    @experimental("ExperimentalTeamsTargeted")
    async def create_targeted(
        self,
        conversation_id: str,
        activity: ActivityParams,
    ) -> SentActivity:
        """
        Create a new targeted activity in a conversation.

        Targeted activities are only visible to the specified recipient.

        .. warning:: Preview
            This API is in preview and may change in the future.
            Diagnostic: ExperimentalTeamsTargeted

        Args:
            conversation_id: The ID of the conversation
            activity: The activity to create

        Returns:
            The created activity
        """
        # TODO: Will be deprecated alongside accessor in ConversationClient
        response = await self.http.post(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities?isTargetedActivity=true",
            json=activity.model_dump(by_alias=True, exclude_none=True),
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.create_targeted,
                conversation_id,
                activity=activity,
                on_response=_set_response_activity_id,
            ),
        )
        response_body = response.json()
        id = response_body.get("id", _PLACEHOLDER_ACTIVITY_ID)
        return SentActivity(id=id, activity_params=activity)

    @experimental("ExperimentalTeamsTargeted")
    async def update_targeted(
        self,
        conversation_id: str,
        activity_id: str,
        activity: ActivityParams,
    ) -> SentActivity:
        """
        Update an existing targeted activity in a conversation.

        .. warning:: Preview
            This API is in preview and may change in the future.
            Diagnostic: ExperimentalTeamsTargeted

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to update
            activity: The updated activity data

        Returns:
            The updated activity
        """
        # TODO: Will be deprecated alongside accessor in ConversationClient
        response = await self.http.put(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities/{activity_id}?isTargetedActivity=true",
            json=activity.model_dump(by_alias=True, exclude_none=True),
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.update_targeted,
                conversation_id,
                activity=activity,
                activity_id=activity_id,
                on_response=_set_response_activity_id,
            ),
        )
        id = response.json()["id"]
        return SentActivity(id=id, activity_params=activity)

    @experimental("ExperimentalTeamsTargeted")
    async def delete_targeted(
        self,
        conversation_id: str,
        activity_id: str,
    ) -> None:
        """
        Delete a targeted activity from a conversation.

        .. warning:: Preview
            This API is in preview and may change in the future.
            Diagnostic: ExperimentalTeamsTargeted

        Args:
            conversation_id: The ID of the conversation
            activity_id: The ID of the activity to delete
        """
        # TODO: Will be deprecated alongside accessor in ConversationClient
        await self.http.delete(
            f"{self._get_service_url()}/v3/conversations/{conversation_id}/activities/{activity_id}?isTargetedActivity=true",
            _metadata=self._create_activity_telemetry_metadata(
                API_OUTBOUND_OPERATIONS.delete_targeted,
                conversation_id,
                activity_id=activity_id,
            ),
        )

    def _create_activity_telemetry_metadata(
        self,
        operation: str,
        conversation_id: str,
        *,
        activity: ActivityParams | None = None,
        activity_id: str | None = None,
        on_response: ApiOutboundResponseHook | None = None,
    ) -> ApiOutboundTelemetryMetadata:
        attributes = {
            API_ATTRIBUTE_NAMES.operation: operation,
            API_ATTRIBUTE_NAMES.service_url: self._get_service_url(),
            API_ATTRIBUTE_NAMES.conversation_id: conversation_id,
        }
        if activity is not None:
            attributes[API_ATTRIBUTE_NAMES.activity_type] = str(activity.type)
        if activity_id is not None:
            attributes[API_ATTRIBUTE_NAMES.activity_id] = activity_id

        return ApiOutboundTelemetryMetadata(
            operation=operation,
            attributes=attributes,
            on_response=on_response,
        )


def _set_response_activity_id(span: Span, response: httpx.Response) -> None:
    response_body = response.json()
    if not isinstance(response_body, dict):
        return
    value = cast(dict[str, object], response_body).get("id")
    if value:
        span.set_attribute(API_ATTRIBUTE_NAMES.activity_id, str(value))
