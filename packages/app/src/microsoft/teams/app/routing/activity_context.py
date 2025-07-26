"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from microsoft.teams.api import (
    ActivityBase,
    ActivityParams,
    ConversationReference,
    MessageActivityInput,
    Resource,
)
from microsoft.teams.common import Storage

T = TypeVar("T", bound=ActivityBase, contravariant=True)

SendCallable = Callable[[str | ActivityParams], Awaitable[Resource]]


class ActivityContext(Generic[T]):
    """Context object passed to activity handlers with middleware support."""

    def __init__(
        self,
        activity: T,
        app_id: str,
        logger: Logger,
        storage: Storage[str, Any],
        conversation_ref: ConversationReference,
        send: SendCallable,
    ):
        self.activity = activity
        self.app_id = app_id
        self.logger = logger
        self.conversation_ref = conversation_ref
        self.send = send

        self._next_handler: Optional[Callable[[], Awaitable[None]]] = None

    async def reply(self, input: str | ActivityParams) -> Resource:
        """Send a reply to the activity."""
        activity = MessageActivityInput(text=input) if isinstance(input, str) else input
        if isinstance(activity, MessageActivityInput):
            block_quote = self._build_block_quote_for_activity(activity)
            if block_quote:
                activity.text = f"{block_quote}\n\n{activity.text}" if activity.text else block_quote
        return await self.send(activity)

    async def next(self) -> None:
        """Call the next middleware in the chain."""
        if self._next_handler:
            await self._next_handler()

    def set_next(self, handler: Callable[[], Awaitable[None]]) -> None:
        """Set the next handler in the middleware chain."""
        self._next_handler = handler

    def _build_block_quote_for_activity(self, activity: ActivityParams) -> Optional[str]:
        if isinstance(activity, MessageActivityInput) and activity.text:
            max_length = 120
            text = activity.text
            truncated_text = f"{text[:max_length]}..." if len(text) > max_length else text

            activity_id = self.activity.id
            from_id = self.activity.from_.id
            from_name = self.activity.from_.name

            return (
                f'<blockquote itemscope="" itemtype="http://schema.skype.com/Reply" itemid="{activity_id}">'
                f'<strong itemprop="mri" itemid="{from_id}">{from_name}</strong>'
                f'<span itemprop="time" itemid="{activity_id}"></span>'
                f'<p itemprop="preview">{truncated_text}</p>'
                f"</blockquote>"
            )
        else:
            self.logger.debug("Skipping building blockquote for activity type: %s", type(self.activity).__name__)
        return None
