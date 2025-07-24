from typing import Awaitable, Callable, Generic, Optional, TypeVar

from microsoft.teams.api import ActivityBase

T = TypeVar("T", bound=ActivityBase, contravariant=True)


class ActivityContext(Generic[T]):
    """Context object passed to activity handlers with middleware support."""

    def __init__(
        self,
        activity: T,
    ):
        self.activity = activity
        self._next_handler: Optional[Callable[[], Awaitable[None]]] = None

    async def next(self) -> None:
        """Call the next middleware in the chain."""
        if self._next_handler:
            await self._next_handler()

    def set_next(self, handler: Callable[[], Awaitable[None]]) -> None:
        """Set the next handler in the middleware chain."""
        self._next_handler = handler
