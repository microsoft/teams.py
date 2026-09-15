"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Optional

from .turn_state import TurnState

_Deleter = Callable[[], Awaitable[None]]
_Saver = Callable[["TurnStateContainer"], Awaitable[None]]


class TurnStateContainer:
    """The state scopes loaded for one turn, together with the identity they
    were loaded for.

    ``conversation`` is always present. ``user`` is ``None`` when the activity has
    no ``from`` identity, so there is no per-user scope to load or persist.

    ``conversation_id``/``user_id`` record the identity this container was loaded
    for. The loader reads them back off the container when saving, so a save can
    never be told to persist under a different key than it was loaded from. That
    guarantee is why they are read-only properties: rebinding either one mid-turn
    would redirect the save to a different conversation or user while the scopes
    still hold the original identity's data.

    Only the identity is bound. ``conversation``/``user`` and the injected
    deleter/saver remain ordinary mutable attributes, and the ``TurnState`` scopes
    stay mutable for the whole turn, which is how ``seal()`` and ``delete()`` work.

    Constructor arguments are keyword-only so the public constructor is not tied to
    positional order and can evolve without breaking callers.
    """

    conversation: TurnState
    user: Optional[TurnState]
    _deleter: Optional[_Deleter]
    _saver: Optional[_Saver]

    def __init__(
        self,
        *,
        conversation: TurnState,
        conversation_id: str,
        user: Optional[TurnState] = None,
        user_id: Optional[str] = None,
        _deleter: Optional[_Deleter] = None,
        _saver: Optional[_Saver] = None,
    ) -> None:
        self._conversation_id = conversation_id
        self._user_id = user_id
        self.conversation = conversation
        self.user = user
        self._deleter = _deleter
        self._saver = _saver

    @property
    def conversation_id(self) -> str:
        """Conversation this container was loaded for. Fixed at construction."""
        return self._conversation_id

    @property
    def user_id(self) -> Optional[str]:
        """User this container was loaded for, if any. Fixed at construction."""
        return self._user_id

    def __repr__(self) -> str:
        return (
            f"{type(self).__qualname__}(conversation={self.conversation!r}, "
            f"conversation_id={self._conversation_id!r}, "
            f"user={self.user!r}, user_id={self._user_id!r})"
        )

    def __eq__(self, other: object) -> bool:
        # Matches the __eq__ the dataclass used to generate: same four fields,
        # injected hooks excluded, and instances of other classes rejected.
        if not isinstance(other, TurnStateContainer) or other.__class__ is not self.__class__:
            return NotImplemented
        return (self.conversation, self._conversation_id, self.user, self._user_id) == (
            other.conversation,
            other._conversation_id,
            other.user,
            other._user_id,
        )

    def seal(self) -> None:
        """Seal every scope so post-turn access raises."""
        self.conversation.seal()
        if self.user is not None:
            self.user.seal()

    async def delete(self) -> None:
        """Clear both scopes and remove them from the backing store.

        The injected deleter removes the keys immediately, then in-memory scopes
        are cleared so state reflects the deletion during the current turn.
        """
        if self._deleter is None:
            raise RuntimeError("State deletion is not available. Call UseState() during service registration.")

        await self._deleter()
        self.conversation.clear()
        self.conversation.mark_clean()
        if self.user is not None:
            self.user.clear()
            self.user.mark_clean()

    async def _save(self) -> None:
        if self._saver is not None:
            await self._saver(self)
