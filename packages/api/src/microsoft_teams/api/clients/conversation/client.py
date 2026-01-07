"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict, Optional, Union

from microsoft_teams.common.http import Client, ClientOptions

from ...models import ConversationResource
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient
from .activity import ActivityParams, ConversationActivityClient
from .member import ConversationMemberClient
from .params import (
    CreateConversationParams,
    GetConversationsParams,
    GetConversationsResponse,
)


class ConversationOperations:
    """Base class for conversation operations."""

    def __init__(self, client: "ConversationClient", conversation_id: str) -> None:
        self._client = client
        self._conversation_id = conversation_id


class ActivityOperations(ConversationOperations):
    """Operations for managing activities in a conversation."""

    async def create(self, activity: ActivityParams, is_targeted: bool = False):
        return await self._client.activities_client.create(self._conversation_id, activity, is_targeted=is_targeted)

    async def update(self, activity_id: str, activity: ActivityParams, is_targeted: bool = False):
        return await self._client.activities_client.update(
            self._conversation_id, activity_id, activity, is_targeted=is_targeted
        )

    async def reply(self, activity_id: str, activity: ActivityParams, is_targeted: bool = False):
        return await self._client.activities_client.reply(
            self._conversation_id, activity_id, activity, is_targeted=is_targeted
        )

    async def delete(self, activity_id: str, is_targeted: bool = False):
        await self._client.activities_client.delete(self._conversation_id, activity_id, is_targeted=is_targeted)

    async def get_members(self, activity_id: str):
        return await self._client.activities_client.get_members(self._conversation_id, activity_id)


class MemberOperations(ConversationOperations):
    """Operations for managing members in a conversation."""

    async def get_all(self):
        return await self._client.members_client.get(self._conversation_id)

    async def get(self, member_id: str):
        return await self._client.members_client.get_by_id(self._conversation_id, member_id)

    async def delete(self, member_id: str) -> None:
        await self._client.members_client.delete(self._conversation_id, member_id)


class ConversationClient(BaseClient):
    """Client for managing Teams conversations."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
    ) -> None:
        """Initialize the client.

        Args:
            service_url: The Teams service URL.
            options: Either an HTTP client instance or client options. If None, a default client is created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(options, api_client_settings)
        self.service_url = service_url

        self._activities_client = ConversationActivityClient(service_url, self.http, self._api_client_settings)
        self._members_client = ConversationMemberClient(service_url, self.http, self._api_client_settings)

    @property
    def http(self) -> Client:
        """Get the HTTP client instance."""
        return self._http

    @http.setter
    def http(self, value: Client) -> None:
        """Set the HTTP client instance and propagate to sub-clients."""
        self._http = value
        self._activities_client.http = value
        self._members_client.http = value

    @property
    def activities_client(self) -> ConversationActivityClient:
        """Get the activities client."""
        return self._activities_client

    @property
    def members_client(self) -> ConversationMemberClient:
        """Get the members client."""
        return self._members_client

    def activities(self, conversation_id: str) -> ActivityOperations:
        """Get activity operations for a conversation.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            An operations object for managing activities in the conversation.
        """
        return ActivityOperations(self, conversation_id)

    def members(self, conversation_id: str) -> MemberOperations:
        """Get member operations for a conversation.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            An operations object for managing members in the conversation.
        """
        return MemberOperations(self, conversation_id)

    async def get(self, params: Optional[GetConversationsParams] = None) -> GetConversationsResponse:
        """Get a list of conversations.

        Args:
            params: Optional parameters for getting conversations.

        Returns:
            A response containing the list of conversations and a continuation token.
        """
        query_params: Dict[str, str] = {}
        if params and params.continuation_token:
            query_params["continuationToken"] = params.continuation_token

        response = await self.http.get(
            f"{self.service_url}/v3/conversations",
            params=query_params,
        )
        return GetConversationsResponse.model_validate(response.json())

    async def create(self, params: CreateConversationParams) -> ConversationResource:
        """Create a new conversation.

        Args:
            params: Parameters for creating the conversation.

        Returns:
            The created conversation resource.
        """
        response = await self.http.post(
            f"{self.service_url}/v3/conversations",
            json=params.model_dump(by_alias=True),
        )
        return ConversationResource.model_validate(response.json())
