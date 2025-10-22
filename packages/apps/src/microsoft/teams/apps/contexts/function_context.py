"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from typing import Generic, Optional, TypeVar

from microsoft.teams.api import (
    Account,
    ActivityParams,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    CreateConversationParams,
    MessageActivityInput,
    SentActivity,
)
from microsoft.teams.cards import AdaptiveCard

from ..http_plugin import HttpPlugin
from .client_context import ClientContext

T = TypeVar("T")


@dataclass(kw_only=True)
class FunctionContext(ClientContext, Generic[T]):
    """
    Context provided to a remote function execution in a Teams app.
    """

    id: Optional[str] = None
    """The ID of the app."""

    name: Optional[str] = None
    """The name of the app."""

    api: ApiClient
    """The API client instance for conversation client."""

    http: HttpPlugin
    """The HTTP plugin instance for sending messages."""

    log: Logger
    """The app logger instance."""

    data: T
    """The function payload."""

    async def send(self, activity: str | ActivityParams | AdaptiveCard) -> Optional[SentActivity]:
        """
        Send an activity to the current conversation.

        Returns None if the conversation ID cannot be determined.
        """
        if self.id is None or self.name is None:
            raise ValueError("app not started")

        conversation_id = await self._resolve_conversation_id(activity)

        if not conversation_id:
            self.log.warning("Cannot send activity: conversation ID could not be resolved")
            return None

        conversation_ref = ConversationReference(
            channel_id="msteams",
            service_url=self.api.service_url,
            bot=Account(id=self.id, name=self.name, role="bot"),
            conversation=ConversationAccount(id=conversation_id, conversation_type="personal"),
        )

        if isinstance(activity, str):
            activity = MessageActivityInput(text=activity)
        elif isinstance(activity, AdaptiveCard):
            activity = MessageActivityInput().add_card(activity)
        else:
            activity = activity

        return await self.http.send(activity, conversation_ref)

    async def _resolve_conversation_id(self, activity: str | ActivityParams | AdaptiveCard) -> Optional[str]:
        """Resolve or create a conversation ID for the current user/context.

        Args:
            activity: The activity to be sent, used to extract conversation info if needed.

        Returns:
            The resolved conversation ID, or None if it could not be determined or created.
        """
        if self._resolved_conversation_id:
            return self._resolved_conversation_id

        self._resolved_conversation_id = self.chat_id or self.channel_id

        # Extract from Activity if available
        if not self._resolved_conversation_id:
            self._resolved_conversation_id = getattr(getattr(activity, "conversation", None), "id", None)

        # Validate that both the bot and user are members of the conversation.
        if self._resolved_conversation_id:
            try:
                member = await self.api.conversations.members_client.get_by_id(
                    self._resolved_conversation_id, self.user_id
                )
                if not member:
                    self.log.warning(
                        f"User {self.user_id} is not a member of conversation {self._resolved_conversation_id}"
                    )
                    self._resolved_conversation_id = None
            except Exception as e:
                self.log.error(f"Failed to get conversation member: {e}")
                self._resolved_conversation_id = None

        else:
            """ Conversation ID can be missing if the app is running in a personal scope. In this case,
            create a conversation between the bot and the user. This will either create a new conversation
            or return a pre-existing one."""
            try:
                conversation_params = CreateConversationParams(
                    bot=Account(id=self.id, name=self.name, role="bot"),  # type: ignore
                    members=[Account(id=self.user_id, role="user", name=self.user_name)],
                    tenant_id=self.tenant_id,
                    is_group=False,
                )
                conversation = await self.api.conversations.create(conversation_params)
                self._resolved_conversation_id = conversation.id
            except Exception as e:
                self.log.error(f"Failed to create conversation: {e}")
                self._resolved_conversation_id = None

        return self._resolved_conversation_id
