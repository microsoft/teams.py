"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

from microsoft.teams.api import Account, ActivityParams, CreateConversationParams, SentActivity
from microsoft.teams.cards import AdaptiveCard

if TYPE_CHECKING:
    from .. import App
from .client_context import ClientContext

T = TypeVar("T", bound=Any)


@dataclass(kw_only=True)
class FunctionContext(ClientContext, Generic[T]):
    """
    Context provided to a remote function execution in a Teams app.
    """

    app: "App"
    """The App instance for sending messages."""

    log: Logger
    """The app logger instance."""

    data: T
    """The function payload."""

    async def send(self, activity: str | ActivityParams | AdaptiveCard) -> Optional[SentActivity]:
        """
        Send an activity to the current conversation.

        Returns None if the conversation ID cannot be determined.
        """
        if self.app.id is None or self.app.name is None:
            raise ValueError("app not started")

        if not self.conversation_id:
            if isinstance(activity, ActivityParams) and activity.conversation:  # pyright: ignore[reportArgumentType]
                self.conversation_id = activity.conversation.id

        if not self.conversation_id:
            """ Conversation ID can be missing if the app is running in a personal scope. In this case, create
                a conversation between the bot and the user. This will either create a new conversation or return
                a pre-existing one."""
            conversation_params = CreateConversationParams(
                bot=Account(id=self.app.id, name=self.app.name, role="bot"),
                members=[Account(id=self.user_id, role="user", name=self.user_name)],
                tenant_id=self.tenant_id,
                is_group=False,
            )
            conversation = await self.app.api.conversations.create(conversation_params)
            self.conversation_id = conversation.id

        return await self.app.send(self.conversation_id, activity)
