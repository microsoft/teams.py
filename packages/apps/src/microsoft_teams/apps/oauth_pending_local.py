"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import threading
from collections import OrderedDict
from time import time
from typing import List, Optional, Tuple

from .oauth_connection import connection_lookup_key

# Process-local fallback for pending sign-in attribution.
#
# When per-turn state is enabled the pending hints live in user state and survive
# restarts and multi-instance deployments. Apps that have not enabled state still
# deserve accurate routing for the common single-instance case, so a sign-in
# started here is remembered in memory just long enough for its callback to come
# back. This mirrors the TypeScript and .NET fallback.
#
# Deliberate limits:
#   * It is a fallback, never a cache. State, when available, always wins, and
#     nothing here causes state to be enabled.
#   * A callback handled by a different process finds nothing and falls back to
#     the existing probing/fan-out behaviour, which is why this can stay small.
#   * Entries are scoped to conversation *and* user, so two users signing in to
#     the same connection in the same conversation never see each other's hints.

_TTL_SECONDS = 300.0
_MAX_ENTRIES = 1000

# (conversation_id, user_id, connection key) -> (original name, created_at, sso_offered)
_Key = Tuple[str, str, str]
_Entry = Tuple[str, float, bool]

_entries: "OrderedDict[_Key, _Entry]" = OrderedDict()
_lock = threading.Lock()


def record(
    conversation_id: str,
    user_id: str,
    connection_name: str,
    *,
    sso_offered: bool,
) -> None:
    """Remember a sign-in that is awaiting its callback."""
    key = _key(conversation_id, user_id, connection_name)
    if key is None:
        return

    with _lock:
        _prune(time())
        # Re-inserting at the end keeps insertion order equal to age order, which
        # is what makes the oldest-first eviction below deterministic.
        _entries.pop(key, None)
        _entries[key] = (connection_name.strip(), time(), sso_offered)
        while len(_entries) > _MAX_ENTRIES:
            _entries.popitem(last=False)


def entries(conversation_id: str, user_id: str) -> List[_Entry]:
    """Unexpired hints for this conversation and user, newest first."""
    if not conversation_id or not user_id:
        return []

    now = time()
    with _lock:
        _prune(now)
        found = [entry for (conv, user, _), entry in _entries.items() if conv == conversation_id and user == user_id]
    return sorted(found, key=lambda entry: (-entry[1], entry[0].lower()))


def clear(conversation_id: str, user_id: str, connection_name: Optional[str] = None) -> None:
    """Drop one connection's hint, or every hint for this conversation and user."""
    if not conversation_id or not user_id:
        return

    target = connection_lookup_key(connection_name) if connection_name is not None else None
    if connection_name is not None and target is None:
        return

    with _lock:
        for key in [
            key
            for key in _entries
            if key[0] == conversation_id and key[1] == user_id and (target is None or key[2] == target)
        ]:
            _entries.pop(key, None)


def replace(conversation_id: str, user_id: str, restored: List[_Entry]) -> None:
    """Restore an exact prior set of hints, preserving their timestamps."""
    if not conversation_id or not user_id:
        return

    clear(conversation_id, user_id)
    with _lock:
        for name, created_at, sso_offered in restored:
            connection_key = connection_lookup_key(name)
            if connection_key is None:
                continue
            _entries[(conversation_id, user_id, connection_key)] = (name.strip(), created_at, sso_offered)


def _key(conversation_id: str, user_id: str, connection_name: str) -> Optional[_Key]:
    if not conversation_id or not user_id:
        return None
    connection_key = connection_lookup_key(connection_name)
    return None if connection_key is None else (conversation_id, user_id, connection_key)


def _prune(now: float) -> None:
    """Drop expired entries. Callers must hold ``_lock``."""
    for key in [key for key, (_, created_at, _) in _entries.items() if now - created_at >= _TTL_SECONDS]:
        _entries.pop(key, None)
