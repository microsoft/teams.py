"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Awaitable, Callable, Generic, Optional, TypeVar

from microsoft.teams.api import ActivityBase, ConversationReference, ConversationResource

T = TypeVar("T", bound=ActivityBase, contravariant=True)

SendCallable = Callable[[str], Awaitable[ConversationResource]]


class ActivityContext(Generic[T]):
    """Context object passed to activity handlers with middleware support."""

    def __init__(
        self, activity: T, app_id: str, logger: Logger, conversation_ref: ConversationReference, send: SendCallable
    ):
        self.activity = activity
        self.app_id = app_id
        self.logger = logger
        self.conversation_ref = conversation_ref
        self.send = send

        self._next_handler: Optional[Callable[[], Awaitable[None]]] = None

    async def next(self) -> None:
        """Call the next middleware in the chain."""
        if self._next_handler:
            await self._next_handler()

    def set_next(self, handler: Callable[[], Awaitable[None]]) -> None:
        """Set the next handler in the middleware chain."""
        self._next_handler = handler
