"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from time import time
from typing import Any, Dict, Iterator, List, Mapping, MutableMapping, Optional, Tuple

from . import oauth_pending_local
from .oauth_connection import connection_lookup_key
from .state import TurnStateContainer

logger = logging.getLogger(__name__)

# Reserved user-state keys recording the sign-ins that are still awaiting a
# callback, used to attribute callbacks that do not name their connection:
#
#   ``__oauth:pending:{connection}``      written whenever a sign-in card is sent
#   ``__oauth:pending:sso:{connection}``  also written when that card offered silent SSO
#
# Each holds an ISO 8601 UTC timestamp.
#
# Connection names are stored verbatim to preserve the casing the app registered,
# while lookups compare case-insensitively. Treat these keys as private: they are
# an implementation detail and app code should neither read nor write them.
_PENDING_OAUTH_KEY_PREFIX = "__oauth:pending:"
_SSO_MARKER_INFIX = "sso:"
_PENDING_OAUTH_SSO_KEY_PREFIX = f"{_PENDING_OAUTH_KEY_PREFIX}{_SSO_MARKER_INFIX}"
_PENDING_OAUTH_MAX_AGE_SECONDS = 5 * 60
_PENDING_OAUTH_MAX_CLOCK_SKEW_SECONDS = 60

# Reserved conversation-state key prefix holding the completed marker for a single
# ``signin/tokenExchange``. The full key is ``__oauth:exchange:{id}`` and the value is an
# ISO 8601 UTC timestamp, mirroring the C# SDK (``OAuthFlow.cs``) so all three SDKs
# describe this state identically. That is design parity, not wire compatibility: the
# SDKs encode the enclosing scope key differently, so they never resolve to the same
# stored document. Conversation scope rather than user scope, because duplicates arrive
# from several of the user's clients but always on the same conversation. Treat the key
# as private: app code should neither read nor write it.
_COMPLETED_EXCHANGE_STATE_KEY_PREFIX = "__oauth:exchange:"

# Completed markers age out on the same schedule as pending sign-ins.
TOKEN_EXCHANGE_DEDUP_TTL_SECONDS = _PENDING_OAUTH_MAX_AGE_SECONDS


@dataclass(frozen=True)
class PendingOAuthSignIn:
    connection_name: str
    created_at: float
    sso_offered: bool


def record_pending_oauth_sign_in(
    state: Optional[TurnStateContainer],
    connection_name: str,
    *,
    sso_offered: bool,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    if state is None or state.user is None:
        oauth_pending_local.record(
            conversation_id or "",
            user_id or "",
            connection_name,
            sso_offered=sso_offered,
        )
        return

    # Reading prunes expired and malformed markers, so a long-lived user state
    # cannot accumulate entries for sign-ins that were never completed.
    _read_markers(state)
    # Drop any earlier attempt for this connection first: the stored casing may
    # differ from the caller's, and only the newest attempt should survive.
    _remove_connection(state, connection_name)

    stamp = _format_timestamp(time())
    state.user[_pending_key(connection_name)] = stamp
    if sso_offered:
        state.user[_sso_key(connection_name)] = stamp


def get_pending_oauth_sign_ins(
    state: Optional[TurnStateContainer],
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> List[PendingOAuthSignIn]:
    if state is None or state.user is None:
        return [
            PendingOAuthSignIn(connection_name=name, created_at=created_at, sso_offered=sso_offered)
            for name, created_at, sso_offered in oauth_pending_local.entries(conversation_id or "", user_id or "")
        ]

    # Newest first, so callers can attribute a callback to the most recent attempt.
    # Connection name breaks ties to keep the order independent of storage order.
    return sorted(
        _read_markers(state).values(),
        key=lambda hint: (-hint.created_at, hint.connection_name.lower()),
    )


def clear_pending_oauth_sign_in(
    state: Optional[TurnStateContainer],
    connection_name: Optional[str] = None,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    if state is None or state.user is None:
        oauth_pending_local.clear(conversation_id or "", user_id or "", connection_name)
        return
    if connection_name is None:
        for key in [key for key in state.user if key.startswith(_PENDING_OAUTH_KEY_PREFIX)]:
            state.user.pop(key, None)
        return

    _remove_connection(state, connection_name)


def mark_pending_oauth_sso_consumed(
    state: Optional[TurnStateContainer],
    connection_name: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    """Retire a hint's silent-SSO marker while keeping it for callback routing.

    Teams renders the sign-in button on the same OAuth card after a silent-SSO
    failure, so the sign-in is still pending even though its SSO attempt is
    spent. Dropping ``sso_offered`` stops the hint from re-attributing later
    ``signin/failure`` callbacks while a follow-up ``signin/verifyState`` can
    still be routed to the right connection. ``created_at`` is preserved so the
    hint expires on its original schedule.
    """
    if state is None or state.user is None:
        oauth_pending_local.mark_sso_consumed(conversation_id or "", user_id or "", connection_name)
        return

    target = connection_lookup_key(connection_name)
    for key, name, is_sso_marker in _iter_markers(state.user):
        if is_sso_marker and connection_lookup_key(name) == target:
            state.user.pop(key, None)


def replace_pending_oauth_sign_ins(
    state: Optional[TurnStateContainer],
    pending: List[PendingOAuthSignIn],
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> None:
    if state is None or state.user is None:
        oauth_pending_local.replace(
            conversation_id or "",
            user_id or "",
            [(hint.connection_name, hint.created_at, hint.sso_offered) for hint in pending],
        )
        return

    clear_pending_oauth_sign_in(state)
    for hint in pending:
        stamp = _format_timestamp(hint.created_at)
        state.user[_pending_key(hint.connection_name)] = stamp
        if hint.sso_offered:
            state.user[_sso_key(hint.connection_name)] = stamp


def _pending_key(connection_name: str) -> str:
    # Trim at the storage boundary so a stray space cannot create a second,
    # unreachable marker for a connection that already has one.
    return f"{_PENDING_OAUTH_KEY_PREFIX}{connection_name.strip()}"


def _sso_key(connection_name: str) -> str:
    return f"{_PENDING_OAUTH_SSO_KEY_PREFIX}{connection_name.strip()}"


def _iter_markers(user: Mapping[str, Any]) -> Iterator[Tuple[str, str, bool]]:
    """Yield ``(key, connection_name, is_sso_marker)`` for every pending marker.

    ``sso:`` is a legal start to a connection name, so ``__oauth:pending:sso:x``
    only counts as the SSO marker for ``x`` when ``x``'s own marker is present;
    otherwise it is the marker for a connection literally named ``sso:x``. The
    two are indistinguishable only when connections ``x`` and ``sso:x`` are both
    registered and ``x`` offered SSO.
    """
    keys = [key for key in user if key.startswith(_PENDING_OAUTH_KEY_PREFIX)]
    present = set(keys)
    for key in keys:
        name = key[len(_PENDING_OAUTH_KEY_PREFIX) :]
        if name.startswith(_SSO_MARKER_INFIX):
            owner = name[len(_SSO_MARKER_INFIX) :]
            if _pending_key(owner) in present:
                yield key, owner, True
                continue
        yield key, name, False


def _read_markers(state: TurnStateContainer) -> Dict[str, PendingOAuthSignIn]:
    """Parse live markers into hints keyed by lowercased connection name.

    Malformed, future-dated and expired markers are dropped from state as they
    are encountered, so a single bad key never invalidates the others.
    """
    user = state.user
    if user is None:
        return {}

    now = time()
    hints: Dict[str, PendingOAuthSignIn] = {}
    sso_owners: Dict[str, str] = {}
    for key, name, is_sso_marker in list(_iter_markers(user)):
        if key not in user:
            # Already discarded while resolving a duplicate.
            continue
        created_at = _parse_timestamp(user.get(key))
        if created_at is None:
            logger.warning("Discarding malformed pending OAuth sign-in state at '%s'.", key)
            user.pop(key, None)
            continue
        if created_at - now > _PENDING_OAUTH_MAX_CLOCK_SKEW_SECONDS:
            logger.warning("Discarding pending OAuth sign-in state at '%s' dated in the future.", key)
            user.pop(key, None)
            continue
        if now - created_at > _PENDING_OAUTH_MAX_AGE_SECONDS:
            logger.warning("Discarding stale pending OAuth sign-in state at '%s'.", key)
            user.pop(key, None)
            continue

        if is_sso_marker:
            sso_owners[name.lower()] = name
            continue

        candidate = PendingOAuthSignIn(connection_name=name, created_at=created_at, sso_offered=False)
        existing = hints.get(name.lower())
        if existing is None:
            hints[name.lower()] = candidate
            continue
        # Two keys differing only in case, which we never write but another SDK
        # might. Keep the newer attempt so the choice is deterministic, and drop
        # the loser's keys rather than leaving them to linger until they expire.
        # ``sso_offered`` ends up true if either casing offered SSO.
        loser, winner = (existing, candidate) if candidate.created_at >= existing.created_at else (candidate, existing)
        _discard_marker(user, loser.connection_name)
        hints[name.lower()] = winner

    # An SSO marker must not outlive the sign-in it describes.
    for lowered, owner in sso_owners.items():
        if lowered not in hints:
            user.pop(_sso_key(owner), None)

    return {
        lowered: replace(hint, sso_offered=True) if lowered in sso_owners else hint for lowered, hint in hints.items()
    }


def _discard_marker(user: MutableMapping[str, Any], connection_name: str) -> None:
    user.pop(_pending_key(connection_name), None)
    user.pop(_sso_key(connection_name), None)


def _remove_connection(state: TurnStateContainer, connection_name: str) -> None:
    user = state.user
    if user is None:
        return

    target = connection_lookup_key(connection_name)
    for key, name, _ in list(_iter_markers(user)):
        if connection_lookup_key(name) == target:
            user.pop(key, None)


def _format_timestamp(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


def _parse_timestamp(raw: Any) -> Optional[float]:
    """Parse a stored ISO 8601 timestamp.

    ``datetime.fromisoformat`` accepts arbitrary fractional-second precision and
    a ``Z`` suffix from Python 3.11 on, which covers .NET's ``DateTimeOffset``
    serialization. A value carrying no offset is read as UTC; forcing the result
    to be timezone-aware also makes ``timestamp()`` pure arithmetic, so it can
    neither raise nor return a non-finite value for any parseable input.
    """
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def completed_token_exchange_state_key(exchange_id: str) -> str:
    """Reserved conversation-state key holding the completed marker for ``exchange_id``."""
    return f"{_COMPLETED_EXCHANGE_STATE_KEY_PREFIX}{exchange_id}"


def has_completed_token_exchange(state: Optional[TurnStateContainer], exchange_id: str) -> bool:
    """Whether ``exchange_id`` has already been redeemed on this conversation.

    Read from conversation state so a duplicate routed to a different process instance
    still short-circuits. Turn state is a last-write-wins document with no ETag/CAS in
    ``Storage``, so this cross-instance layer is best-effort; the caller's in-process
    guard is what makes same-instance dedup atomic. The C# SDK carries the same caveat.
    """
    if state is None or not exchange_id:
        return False

    key = completed_token_exchange_state_key(exchange_id)
    raw = state.conversation.get(key)
    if raw is None:
        return False

    completed_at = _parse_completed_at(raw)
    if completed_at is None:
        logger.warning("Discarding malformed completed OAuth token exchange state.")
        state.conversation.pop(key, None)
        return False
    if time() - completed_at > TOKEN_EXCHANGE_DEDUP_TTL_SECONDS:
        state.conversation.pop(key, None)
        return False
    return True


def record_completed_token_exchange(state: Optional[TurnStateContainer], exchange_id: str) -> None:
    """Persist the completed marker for ``exchange_id``.

    The marker is deliberately never cleared when the exchange finishes: a late
    duplicate from a second Teams endpoint can arrive after the original settles, and
    an already-removed marker would let it run as a brand new exchange. Markers are
    pruned only once they age past :data:`TOKEN_EXCHANGE_DEDUP_TTL_SECONDS`.
    """
    if state is None or not exchange_id:
        return
    _write_completed_token_exchange(state, exchange_id)


def _write_completed_token_exchange(state: TurnStateContainer, exchange_id: str) -> None:
    """Single write chokepoint for completed markers.

    Pruning here keeps the invariant that the conversation document never carries an
    expired or unparsable marker, no matter which caller wrote it.
    """
    _prune_completed_token_exchanges(state)
    state.conversation[completed_token_exchange_state_key(exchange_id)] = _format_timestamp(time())


def _prune_completed_token_exchanges(state: TurnStateContainer) -> None:
    """Drop expired or malformed markers so the conversation document stays bounded."""
    now = time()
    for key in list(state.conversation):
        if not key.startswith(_COMPLETED_EXCHANGE_STATE_KEY_PREFIX):
            continue
        completed_at = _parse_completed_at(state.conversation.get(key))
        if completed_at is None or now - completed_at > TOKEN_EXCHANGE_DEDUP_TTL_SECONDS:
            state.conversation.pop(key, None)


def _parse_completed_at(raw: Any) -> Optional[float]:
    """Parse a stored marker, rejecting timestamps too far in the future.

    ``_parse_timestamp`` already rejects anything that is not a parseable ISO 8601
    string. The extra guard is for clock skew between instances: a marker stamped well
    ahead of this instance's clock would otherwise read as fresh long past its TTL.
    """
    completed_at = _parse_timestamp(raw)
    if completed_at is None:
        return None
    if completed_at > time() + _PENDING_OAUTH_MAX_CLOCK_SKEW_SECONDS:
        return None
    return completed_at
