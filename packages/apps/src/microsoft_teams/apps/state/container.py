"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Awaitable, Callable, Optional

from .turn_state import TurnState

_Deleter = Callable[[], Awaitable[None]]


@dataclass
class TurnStateContainer:
    """The state scopes loaded for one turn, together with the identity they
    were loaded for.

    ``conversation`` is always present. ``user`` is ``None`` when the activity has
    no ``from`` identity, so there is no per-user scope to load or persist.

    ``conversation_id``/``user_id`` record the identity this container was loaded
    for. The loader reads them back off the container when saving, so a save can
    never be told to persist under a different key than it was loaded from.
    """

    conversation: TurnState
    user: Optional[TurnState] = None
    conversation_id: str = ""
    user_id: Optional[str] = None
    _deleter: Optional[_Deleter] = field(default=None, repr=False, compare=False)

    def seal(self) -> None:
        """Seal every scope so post-turn access raises."""
        self.conversation.seal()
        if self.user is not None:
            self.user.seal()

    async def delete(self) -> None:
        """Clear both scopes and remove them from the backing store.

        Clearing marks the scopes empty so a later save is a no-op, and the
        injected deleter removes the keys immediately.
        """
        self.conversation.clear()
        if self.user is not None:
            self.user.clear()
        if self._deleter is not None:
            await self._deleter()
