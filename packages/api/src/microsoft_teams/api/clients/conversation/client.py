"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Union

from microsoft_teams.common.http import Client, ClientOptions
from typing_extensions import deprecated

from ...models import AgenticIdentity, ConversationResource
from ...models.message import MessageReactionType
from .._auth_provider_interceptor import AGENTIC_IDENTITY_EXTENSION
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient
from ..reaction import ReactionClient
from .activity import ActivityParams, ConversationActivityClient
from .member import ConversationMemberClient
from .params import CreateConversationParams


class ConversationOperations:
    """Base class for conversation operations."""

    def __init__(self, client: "ConversationClient", conversation_id: str) -> None:
        self._client = client
        self._conversation_id = conversation_id


class ActivityOperations(ConversationOperations):
    """Operations for managing activities in a conversation."""

    async def create(
        self,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        return await self._client.activities_client.create(
            self._conversation_id, activity, service_url=service_url, agentic_identity=agentic_identity
        )

    async def update(
        self,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        return await self._client.activities_client.update(
            self._conversation_id, activity_id, activity, service_url=service_url, agentic_identity=agentic_identity
        )

    async def reply(
        self,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        return await self._client.activities_client.reply(
            self._conversation_id, activity_id, activity, service_url=service_url, agentic_identity=agentic_identity
        )

    async def delete(
        self,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        await self._client.activities_client.delete(
            self._conversation_id, activity_id, service_url=service_url, agentic_identity=agentic_identity
        )

    async def get_members(
        self,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        return await self._client.activities_client.get_members(
            self._conversation_id, activity_id, service_url=service_url, agentic_identity=agentic_identity
        )

    async def create_targeted(
        self,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
    ):
        """Create a new targeted activity visible only to the specified recipient."""
        return await self._client.activities_client.create_targeted(
            self._conversation_id, activity, service_url=service_url
        )

    async def update_targeted(
        self,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
    ):
        """Update an existing targeted activity."""
        return await self._client.activities_client.update_targeted(
            self._conversation_id, activity_id, activity, service_url=service_url
        )

    async def delete_targeted(
        self,
        activity_id: str,
        *,
        service_url: str | None = None,
    ):
        """Delete a targeted activity."""
        await self._client.activities_client.delete_targeted(
            self._conversation_id, activity_id, service_url=service_url
        )


class MemberOperations(ConversationOperations):
    """Operations for managing members in a conversation."""

    async def get_all(self, *, service_url: str | None = None, agentic_identity: AgenticIdentity | None = None):
        return await self._client.members_client.get(
            self._conversation_id, service_url=service_url, agentic_identity=agentic_identity
        )

    async def get_paged(
        self,
        page_size: Optional[int] = None,
        continuation_token: Optional[str] = None,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        return await self._client.members_client.get_paged(
            self._conversation_id,
            page_size,
            continuation_token,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def get(
        self, member_id: str, *, service_url: str | None = None, agentic_identity: AgenticIdentity | None = None
    ):
        return await self._client.members_client.get_by_id(
            self._conversation_id, member_id, service_url=service_url, agentic_identity=agentic_identity
        )


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
        self.service_url = service_url.rstrip("/")

        self._activities_client = ConversationActivityClient(
            self.service_url,
            self.http,
            self._api_client_settings,
        )
        self._members_client = ConversationMemberClient(
            self.service_url,
            self.http,
            self._api_client_settings,
        )
        self._reactions_client = ReactionClient(self.service_url, self.http, self._api_client_settings)

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
        self._reactions_client.http = value

    @property
    def activities_client(self) -> ConversationActivityClient:
        """Get the activities client."""
        return self._activities_client

    @property
    def members_client(self) -> ConversationMemberClient:
        """Get the members client."""
        return self._members_client

    @deprecated(
        "Use the flattened activity methods on `ConversationClient` instead "
        "(e.g. `conversations.create_activity(conversation_id, ...)`). "
        "This grouped accessor will be removed in a future release."
    )
    def activities(self, conversation_id: str) -> ActivityOperations:
        """Get activity operations for a conversation.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            An operations object for managing activities in the conversation.
        """
        return ActivityOperations(self, conversation_id)

    @deprecated(
        "Use the flattened member methods on `ConversationClient` instead "
        "(e.g. `conversations.get_members(conversation_id)`). "
        "This grouped accessor will be removed in a future release."
    )
    def members(self, conversation_id: str) -> MemberOperations:
        """Get member operations for a conversation.

        Args:
            conversation_id: The ID of the conversation.

        Returns:
            An operations object for managing members in the conversation.
        """
        return MemberOperations(self, conversation_id)

    async def create_activity(self, conversation_id: str, activity: ActivityParams):
        """Create an activity in a conversation."""
        return await self._activities_client.create(conversation_id, activity)

    async def update_activity(self, conversation_id: str, activity_id: str, activity: ActivityParams):
        """Update an activity in a conversation."""
        return await self._activities_client.update(conversation_id, activity_id, activity)

    async def reply_to_activity(self, conversation_id: str, activity_id: str, activity: ActivityParams):
        """Reply to an activity in a conversation."""
        return await self._activities_client.reply(conversation_id, activity_id, activity)

    async def delete_activity(self, conversation_id: str, activity_id: str):
        """Delete an activity in a conversation."""
        return await self._activities_client.delete(conversation_id, activity_id)

    async def get_activity_members(self, conversation_id: str, activity_id: str):
        """Get the members of an activity in a conversation."""
        return await self._activities_client.get_members(conversation_id, activity_id)

    async def create_targeted_activity(self, conversation_id: str, activity: ActivityParams):
        """Create a targeted activity in a conversation."""
        return await self._activities_client.create_targeted(conversation_id, activity)

    async def update_targeted_activity(self, conversation_id: str, activity_id: str, activity: ActivityParams):
        """Update a targeted activity in a conversation."""
        return await self._activities_client.update_targeted(conversation_id, activity_id, activity)

    async def delete_targeted_activity(self, conversation_id: str, activity_id: str):
        """Delete a targeted activity in a conversation."""
        return await self._activities_client.delete_targeted(conversation_id, activity_id)

    async def get_members(self, conversation_id: str):
        """Get the members of a conversation."""
        return await self._members_client.get(conversation_id)

    async def get_member_by_id(self, conversation_id: str, member_id: str):
        """Get a member of a conversation by id."""
        return await self._members_client.get_by_id(conversation_id, member_id)

    async def get_paged_members(
        self,
        conversation_id: str,
        page_size: Optional[int] = None,
        continuation_token: Optional[str] = None,
    ):
        """Get paged members of a conversation."""
        return await self._members_client.get_paged(conversation_id, page_size, continuation_token)

    async def add_reaction(self, conversation_id: str, activity_id: str, reaction_type: MessageReactionType) -> None:
        """Add a reaction to an activity in a conversation."""
        return await self._reactions_client.add(conversation_id, activity_id, reaction_type)

    async def delete_reaction(self, conversation_id: str, activity_id: str, reaction_type: MessageReactionType) -> None:
        """Delete a reaction from an activity in a conversation."""
        return await self._reactions_client.delete(conversation_id, activity_id, reaction_type)

    async def create(
        self,
        params: CreateConversationParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> ConversationResource:
        """Create a new conversation.

        Args:
            params: Parameters for creating the conversation.

        Returns:
            The created conversation resource.
        """
        response = await self.http.post(
            f"{self._get_service_url(service_url)}/v3/conversations",
            json=params.model_dump(by_alias=True, exclude_none=True),
            extensions={AGENTIC_IDENTITY_EXTENSION: agentic_identity},
        )
        return ConversationResource.model_validate(response.json())
