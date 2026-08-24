"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, cast
from urllib.parse import quote

from microsoft_teams.common import Storage

from .container import TurnStateContainer
from .options import StateOptions
from .turn_state import TurnState

logger = logging.getLogger(__name__)


class TurnStateLoader:
    """Loads and persists :class:`TurnState` scopes over a ``Storage`` backend.

    Values are stored as JSON **strings** so any ``Storage`` implementation works
    regardless of how it serializes values. Expiry and other write behavior are
    configured directly on the selected storage provider.
    """

    def __init__(self, storage: Optional[Storage[str, Any]] = None, options: Optional[StateOptions] = None) -> None:
        self._options = options or StateOptions()
        resolved = storage if storage is not None else self._options.storage
        if resolved is None:
            raise ValueError("TurnStateLoader requires a Storage backend (pass one explicitly or via StateOptions).")
        self._storage: Storage[str, Any] = resolved

    @property
    def options(self) -> StateOptions:
        return self._options

    def conversation_key(self, conversation_id: str) -> str:
        """Key for the conversation-scoped blob."""
        return f"{self._options.key_prefix}:conv:{quote(conversation_id, safe='')}"

    def user_key(self, conversation_id: str, user_id: str) -> str:
        """Key for the user-scoped blob."""
        return f"{self._options.key_prefix}:user:{quote(conversation_id, safe='')}:{quote(user_id, safe='')}"

    async def load(self, conversation_id: str, user_id: Optional[str] = None) -> TurnStateContainer:
        """Load both scopes for the turn. ``user`` is ``None`` when ``user_id`` is."""
        conversation = await self._load_scope(self.conversation_key(conversation_id))

        user: Optional[TurnState] = None
        if user_id is not None:
            user = await self._load_scope(self.user_key(conversation_id, user_id))

        async def _delete() -> None:
            await self.delete(conversation_id, user_id)

        return TurnStateContainer(
            conversation=conversation,
            user=user,
            conversation_id=conversation_id,
            user_id=user_id,
            _deleter=_delete,
        )

    async def save(self, container: TurnStateContainer) -> None:
        """Persist dirty scopes under the identity the container was loaded for.

        Identity is read off the container (``conversation_id``/``user_id``), so a
        save always targets the same keys the container was loaded from.
        Empty-but-dirty scopes are deleted.
        """
        if not container.conversation_id:
            raise ValueError("TurnStateContainer.conversation_id must be set to save state.")
        if container.user is not None and not container.user_id:
            raise ValueError("TurnStateContainer.user_id must be set to save user state.")

        pending_deletes: list[str] = []
        pending_sets: list[tuple[str, str]] = []
        pending_clean: list[TurnState] = []
        self._prepare_scope_save(
            self.conversation_key(container.conversation_id),
            container.conversation,
            pending_deletes,
            pending_sets,
            pending_clean,
        )
        if container.user is not None and container.user_id is not None:
            self._prepare_scope_save(
                self.user_key(container.conversation_id, container.user_id),
                container.user,
                pending_deletes,
                pending_sets,
                pending_clean,
            )

        for key in pending_deletes:
            await self._storage.async_delete(key)
        for key, value in pending_sets:
            await self._storage.async_set(key, value)
        for scope in pending_clean:
            scope.mark_clean()

    async def delete(self, conversation_id: str, user_id: Optional[str] = None) -> None:
        """Delete both scope blobs for the turn's identity."""
        await self._storage.async_delete(self.conversation_key(conversation_id))
        if user_id is not None:
            await self._storage.async_delete(self.user_key(conversation_id, user_id))

    async def _load_scope(self, key: str) -> TurnState:
        raw = await self._storage.async_get(key)
        if raw is None:
            return TurnState()

        data = self._deserialize(raw)
        if data is None:
            await self._storage.async_delete(key)
            return TurnState()

        return TurnState(data)

    def _prepare_scope_save(
        self,
        key: str,
        scope: TurnState,
        pending_deletes: list[str],
        pending_sets: list[tuple[str, str]],
        pending_clean: list[TurnState],
    ) -> None:
        if not scope.is_dirty:
            return
        if scope.is_empty:
            pending_deletes.append(key)
            pending_clean.append(scope)
            return
        pending_sets.append((key, json.dumps(scope.to_dict())))
        pending_clean.append(scope)

    def _deserialize(self, raw: Any) -> Optional[Dict[str, Any]]:
        """Parse a stored blob.

        Never raises: unreadable or malformed blobs are treated as missing.
        """
        if isinstance(raw, dict):
            parsed: Any = cast(Dict[Any, Any], raw)
        elif isinstance(raw, str):
            try:
                parsed = json.loads(raw)
            except ValueError:
                logger.debug("Discarding unreadable state blob at load")
                return None
        else:
            return None

        if not isinstance(parsed, dict):
            return None
        mapping = cast(Dict[object, Any], parsed)
        if not all(isinstance(key, str) for key in mapping):
            return None
        return cast(Dict[str, Any], mapping)
