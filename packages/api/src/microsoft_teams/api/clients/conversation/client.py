"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Callable, Optional, Union

from microsoft_teams.common.http import Client, ClientOptions
from typing_extensions import deprecated

from ...activities import SentActivity
from ...diagnostics._outbound import ensure_outbound_telemetry_middleware
from ...models import AgenticIdentity, ConversationResource, TeamsChannelAccount
from ...models.message import MessageReactionType
from ..api_client_settings import ApiClientSettings
from ..base_client import BaseClient
from ..reaction import ReactionClient
from .activity import ActivityParams, ConversationActivityClient
from .member import ConversationMemberClient
from .params import CreateConversationParams

ConversationScopeFactory = Callable[[str | None, AgenticIdentity | None], "ConversationClient"]


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
    ) -> SentActivity:
        return await self._client.create_activity(
            self._conversation_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def update(
        self,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        return await self._client.update_activity(
            self._conversation_id,
            activity_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def reply(
        self,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        return await self._client.reply_to_activity(
            self._conversation_id,
            activity_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def delete(
        self,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> None:
        await self._client.delete_activity(
            self._conversation_id,
            activity_id,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def get_members(
        self,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> list[TeamsChannelAccount]:
        return await self._client.get_activity_members(
            self._conversation_id,
            activity_id,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def create_targeted(
        self,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Create a new targeted activity visible only to the specified recipient."""
        return await self._client.create_targeted_activity(
            self._conversation_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def update_targeted(
        self,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Update an existing targeted activity."""
        return await self._client.update_targeted_activity(
            self._conversation_id,
            activity_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def delete_targeted(
        self,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> None:
        """Delete a targeted activity."""
        await self._client.delete_targeted_activity(
            self._conversation_id,
            activity_id,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )


class MemberOperations(ConversationOperations):
    """Operations for managing members in a conversation."""

    async def get_all(self):
        return await self._client.members_client.get(self._conversation_id)

    async def get_paged(
        self,
        page_size: Optional[int] = None,
        continuation_token: Optional[str] = None,
    ):
        return await self._client.members_client.get_paged(
            self._conversation_id,
            page_size,
            continuation_token,
        )

    async def get(self, member_id: str):
        return await self._client.members_client.get_by_id(self._conversation_id, member_id)


class ConversationClient(BaseClient):
    """Client for managing Teams conversations."""

    def __init__(
        self,
        service_url: str,
        options: Optional[Union[Client, ClientOptions]] = None,
        api_client_settings: Optional[ApiClientSettings] = None,
        scope_factory: ConversationScopeFactory | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            service_url: The Teams service URL.
            options: Either an HTTP client instance or client options. If None, a default client is created.
            api_client_settings: Optional API client settings.
        """
        super().__init__(options, api_client_settings)
        self.service_url = service_url.rstrip("/")
        self._scope_factory = scope_factory

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
        ensure_outbound_telemetry_middleware(value)
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

    def _scoped_client(
        self,
        service_url: str | None,
        agentic_identity: AgenticIdentity | None,
    ) -> "ConversationClient":
        if (service_url is None and agentic_identity is None) or self._scope_factory is None:
            return self
        return self._scope_factory(service_url, agentic_identity)

    async def create_activity(
        self,
        conversation_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Create an activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.create_activity(conversation_id, activity)
        return await self._activities_client.create(
            conversation_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def update_activity(
        self,
        conversation_id: str,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Update an activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.update_activity(conversation_id, activity_id, activity)
        return await self._activities_client.update(
            conversation_id,
            activity_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def reply_to_activity(
        self,
        conversation_id: str,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Reply to an activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.reply_to_activity(conversation_id, activity_id, activity)
        return await self._activities_client.reply(
            conversation_id,
            activity_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def delete_activity(
        self,
        conversation_id: str,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> None:
        """Delete an activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.delete_activity(conversation_id, activity_id)
        return await self._activities_client.delete(
            conversation_id,
            activity_id,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def get_activity_members(
        self,
        conversation_id: str,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> list[TeamsChannelAccount]:
        """Get the members of an activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.get_activity_members(conversation_id, activity_id)
        return await self._activities_client.get_members(
            conversation_id,
            activity_id,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def create_targeted_activity(
        self,
        conversation_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Create a targeted activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.create_targeted_activity(conversation_id, activity)
        return await self._activities_client.create_targeted(
            conversation_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def update_targeted_activity(
        self,
        conversation_id: str,
        activity_id: str,
        activity: ActivityParams,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> SentActivity:
        """Update a targeted activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.update_targeted_activity(conversation_id, activity_id, activity)
        return await self._activities_client.update_targeted(
            conversation_id,
            activity_id,
            activity,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

    async def delete_targeted_activity(
        self,
        conversation_id: str,
        activity_id: str,
        *,
        service_url: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> None:
        """Delete a targeted activity in a conversation."""
        scoped_client = self._scoped_client(service_url, agentic_identity)
        if scoped_client is not self:
            return await scoped_client.delete_targeted_activity(conversation_id, activity_id)
        return await self._activities_client.delete_targeted(
            conversation_id,
            activity_id,
            service_url=service_url,
            agentic_identity=agentic_identity,
        )

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
    ) -> ConversationResource:
        """Create a new conversation.

        Args:
            params: Parameters for creating the conversation.

        Returns:
            The created conversation resource.
        """
        response = await self.http.post(
            f"{self._get_service_url()}/v3/conversations",
            json=params.model_dump(by_alias=True, exclude_none=True),
        )
        return ConversationResource.model_validate(response.json())
