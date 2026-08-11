"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional, cast

from microsoft_teams.common import Storage

from .container import TurnStateContainer
from .options import StateOptions
from .turn_state import TurnState

logger = logging.getLogger(__name__)


class TurnStateLoader:
    """Loads and persists :class:`TurnState` scopes over a ``Storage`` backend.

    Values are stored as JSON **strings** so any ``Storage`` implementation works
    regardless of how it serializes values. Each blob carries a save timestamp
    that powers the loader-applied TTL, since ``Storage`` has no native expiry.

    """

    def __init__(self, storage: Optional[Storage[str, str]] = None, options: Optional[StateOptions] = None) -> None:
        self._options = options or StateOptions()
        resolved = storage if storage is not None else self._options.storage
        if resolved is None:
            raise ValueError("TurnStateLoader requires a Storage backend (pass one explicitly or via StateOptions).")
        self._storage: Storage[str, str] = resolved

    @property
    def options(self) -> StateOptions:
        return self._options

    def conversation_key(self, conversation_id: str) -> str:
        """Key for the conversation-scoped blob (mirrors C#'s ``ts:conv:{id}``)."""
        return f"{self._options.key_prefix}:conv:{conversation_id}"

    def user_key(self, conversation_id: str, user_id: str) -> str:
        """Key for the user-scoped blob (mirrors C#'s ``ts:user:{convId}:{userId}``)."""
        return f"{self._options.key_prefix}:user:{conversation_id}:{user_id}"

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
        await self._save_scope(self.conversation_key(container.conversation_id), container.conversation)
        if container.user is not None and container.user_id is not None:
            await self._save_scope(self.user_key(container.conversation_id, container.user_id), container.user)

    async def delete(self, conversation_id: str, user_id: Optional[str] = None) -> None:
        """Delete both scope blobs for the turn's identity."""
        await self._storage.async_delete(self.conversation_key(conversation_id))
        if user_id is not None:
            await self._storage.async_delete(self.user_key(conversation_id, user_id))

    async def _load_scope(self, key: str) -> TurnState:
        raw = await self._storage.async_get(key)
        return TurnState(self._deserialize(raw))

    async def _save_scope(self, key: str, scope: TurnState) -> None:
        if not scope.is_dirty:
            return
        if scope.is_empty:
            await self._storage.async_delete(key)
            return
        blob = {"ts": time.time(), "data": scope.to_dict()}
        await self._storage.async_set(key, json.dumps(blob))

    def _deserialize(self, raw: Optional[Any]) -> Dict[str, Any]:
        """Turn a stored blob back into a scope dict.

        Never raises: an absent, unreadable, or expired blob is treated as an
        empty scope.
        """
        if not raw:
            return {}
        try:
            parsed: Any = json.loads(raw)
        except (ValueError, TypeError):
            logger.debug("Discarding unreadable state blob at load")
            return {}

        if not isinstance(parsed, dict):
            return {}
        blob = cast(Dict[str, Any], parsed)

        if self._options.ttl is not None:
            saved_at = blob.get("ts")
            if not isinstance(saved_at, (int, float)):
                return {}
            if (time.time() - saved_at) > self._options.ttl:
                return {}

        data = blob.get("data")
        if isinstance(data, dict):
            return cast(Dict[str, Any], data)
        return {}
