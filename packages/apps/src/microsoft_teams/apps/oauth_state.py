"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from dataclasses import dataclass, replace
from math import isfinite
from time import time
from typing import Any, Dict, List, Optional, cast

from .state import TurnStateContainer

logger = logging.getLogger(__name__)

# Reserved user-state key holding the pending sign-in hints used to attribute
# connection-less OAuth callbacks. The stored document is
# ``{"version": 1, "hints": [{"connection_name", "created_at", "sso_offered"}, ...]}``
# with at most one hint per connection (compared case-insensitively) and hints
# ordered newest-first. Treat it as private; app code should not read or write it.
_PENDING_OAUTH_STATE_KEY = "__oauth:pending"
_PENDING_OAUTH_STATE_VERSION = 1
_PENDING_OAUTH_MAX_AGE_SECONDS = 5 * 60
_PENDING_OAUTH_MAX_CLOCK_SKEW_SECONDS = 60


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
) -> None:
    if state is None or state.user is None:
        return

    existing = [
        hint for hint in get_pending_oauth_sign_ins(state) if hint.connection_name.lower() != connection_name.lower()
    ]
    pending = [
        PendingOAuthSignIn(
            connection_name=connection_name,
            created_at=time(),
            sso_offered=sso_offered,
        ),
        *existing,
    ]
    _write_pending_oauth_sign_ins(state, pending)


def get_pending_oauth_sign_ins(state: Optional[TurnStateContainer]) -> List[PendingOAuthSignIn]:
    if state is None or state.user is None:
        return []

    raw = state.user.get(_PENDING_OAUTH_STATE_KEY)
    if raw is None:
        return []
    if not isinstance(raw, dict):
        _discard_malformed(state)
        return []

    value = cast(Dict[str, Any], raw)
    raw_hints = value.get("hints")
    if value.get("version") != _PENDING_OAUTH_STATE_VERSION or not isinstance(raw_hints, list):
        _discard_malformed(state)
        return []

    now = time()
    pending: List[PendingOAuthSignIn] = []
    seen: set[str] = set()
    stale_found = False
    for raw_hint in cast(List[Any], raw_hints):
        hint = _parse_hint(raw_hint)
        if hint is None:
            _discard_malformed(state)
            return []
        if hint.created_at > now + _PENDING_OAUTH_MAX_CLOCK_SKEW_SECONDS:
            _discard_malformed(state)
            return []
        if now - hint.created_at > _PENDING_OAUTH_MAX_AGE_SECONDS:
            stale_found = True
            continue
        key = hint.connection_name.lower()
        if key in seen:
            continue
        seen.add(key)
        pending.append(hint)

    # Hints are stored newest-first, so ``seen`` already keeps the freshest entry per
    # connection. Sort anyway so callers can rely on the ordering even if the stored
    # document was written by a different version or edited by hand.
    pending.sort(key=lambda hint: hint.created_at, reverse=True)
    if stale_found:
        logger.warning("Discarding stale pending OAuth sign-in state.")
        _write_pending_oauth_sign_ins(state, pending)
    return pending


def clear_pending_oauth_sign_in(
    state: Optional[TurnStateContainer],
    connection_name: Optional[str] = None,
) -> None:
    if state is None or state.user is None:
        return
    if connection_name is None:
        state.user.pop(_PENDING_OAUTH_STATE_KEY, None)
        return

    pending = [
        hint for hint in get_pending_oauth_sign_ins(state) if hint.connection_name.lower() != connection_name.lower()
    ]
    _write_pending_oauth_sign_ins(state, pending)


def mark_pending_oauth_sso_consumed(
    state: Optional[TurnStateContainer],
    connection_name: str,
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
        return

    pending = get_pending_oauth_sign_ins(state)
    updated = [
        replace(hint, sso_offered=False) if hint.connection_name.lower() == connection_name.lower() else hint
        for hint in pending
    ]
    if updated != pending:
        _write_pending_oauth_sign_ins(state, updated)


def replace_pending_oauth_sign_ins(
    state: Optional[TurnStateContainer],
    pending: List[PendingOAuthSignIn],
) -> None:
    if state is not None:
        _write_pending_oauth_sign_ins(state, pending)


def _parse_hint(raw: Any) -> Optional[PendingOAuthSignIn]:
    if not isinstance(raw, dict):
        return None

    value = cast(Dict[str, Any], raw)
    connection_name = value.get("connection_name")
    created_at = value.get("created_at")
    sso_offered = value.get("sso_offered")
    if (
        not isinstance(connection_name, str)
        or not connection_name
        or isinstance(created_at, bool)
        or not isinstance(created_at, (int, float))
        or not isinstance(sso_offered, bool)
    ):
        return None

    try:
        normalized_created_at = float(created_at)
    except (OverflowError, TypeError, ValueError):
        return None
    if not isfinite(normalized_created_at):
        return None

    return PendingOAuthSignIn(
        connection_name=connection_name,
        created_at=normalized_created_at,
        sso_offered=sso_offered,
    )


def _write_pending_oauth_sign_ins(
    state: TurnStateContainer,
    pending: List[PendingOAuthSignIn],
) -> None:
    if state.user is None:
        return
    if not pending:
        state.user.pop(_PENDING_OAUTH_STATE_KEY, None)
        return

    # Every mutation funnels through here, so normalizing the order once keeps the
    # stored ``hints`` list newest-first no matter which caller wrote it. The sort is
    # stable, so hints sharing a ``created_at`` keep the order they were inserted in.
    ordered = sorted(pending, key=lambda hint: hint.created_at, reverse=True)
    state.user[_PENDING_OAUTH_STATE_KEY] = {
        "version": _PENDING_OAUTH_STATE_VERSION,
        "hints": [
            {
                "connection_name": hint.connection_name,
                "created_at": hint.created_at,
                "sso_offered": hint.sso_offered,
            }
            for hint in ordered
        ],
    }


def _discard_malformed(state: TurnStateContainer) -> None:
    logger.warning("Discarding malformed pending OAuth sign-in state.")
    if state.user is not None:
        state.user.pop(_PENDING_OAUTH_STATE_KEY, None)
