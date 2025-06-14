"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional, Union

from microsoft.teams.common.http import Client, ClientOptions

from ...models import ConversationResource
from .activity import ConversationActivityClient
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

    async def create(self, activity: Any) -> Any:
        return await self._client._activities.create(self._conversation_id, activity)

    async def update(self, activity_id: str, activity: Any) -> Any:
        return await self._client._activities.update(self._conversation_id, activity_id, activity)

    async def reply(self, activity_id: str, activity: Any) -> Any:
        return await self._client._activities.reply(self._conversation_id, activity_id, activity)

    async def delete(self, activity_id: str) -> None:
        await self._client._activities.delete(self._conversation_id, activity_id)

    async def get_members(self, activity_id: str) -> Any:
        return await self._client._activities.get_members(self._conversation_id, activity_id)


class MemberOperations(ConversationOperations):
    """Operations for managing members in a conversation."""

    async def get_all(self) -> Any:
        return await self._client._members.get(self._conversation_id)

    async def get(self, member_id: str) -> Any:
        return await self._client._members.get_by_id(self._conversation_id, member_id)

    async def delete(self, member_id: str) -> None:
        await self._client._members.delete(self._conversation_id, member_id)


class ConversationClient:
    """Client for managing Teams conversations."""

    def __init__(self, service_url: str, options: Union[Client, ClientOptions] = None) -> None:
        """Initialize the client.

        Args:
            service_url: The Teams service URL.
            options: Either an HTTP client instance or client options. If None, a default client is created.
        """
        self.service_url = service_url

        if isinstance(options, Client):
            self._http = options
        else:
            self._http = Client(options or ClientOptions())

        self._activities = ConversationActivityClient(service_url, self._http)
        self._members = ConversationMemberClient(service_url, self._http)

    @property
    def http(self) -> Client:
        """Get the HTTP client.

        Returns:
            The HTTP client instance.
        """
        return self._http

    @http.setter
    def http(self, client: Client) -> None:
        """Set the HTTP client.

        Args:
            client: The HTTP client to use.
        """
        self._http = client
        # Update sub-clients with new HTTP client
        self._activities = ConversationActivityClient(self.service_url, client)
        self._members = ConversationMemberClient(self.service_url, client)

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
        query_params = {}
        if params and params.continuation_token:
            query_params["continuationToken"] = params.continuation_token

        response = await self._http.get(
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
        response = await self._http.post(
            f"{self.service_url}/v3/conversations",
            json=params.model_dump(by_alias=True),
        )
        return ConversationResource.model_validate(response.json())
