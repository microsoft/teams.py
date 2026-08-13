"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from microsoft_teams.common import Storage


@dataclass(frozen=True)
class StateOptions:
    """Configuration for the per-turn state layer.

    Scope keys are namespaced
    under ``key_prefix`` and expiry is applied by the loader, since ``Storage``
    has no native TTL concept.
    """

    storage: Optional[Storage[str, str]] = None
    """Backing store for state blobs. When ``None`` the loader must be given one."""

    key_prefix: str = "ts"
    """Namespace prefix for scope keys (``{prefix}:conv:...`` / ``{prefix}:user:...``)."""

    ttl: Optional[int] = None
    """Optional lazy, sliding time-to-live in **seconds**.

    The loader stamps each successful state write and treats the scope as
    expired when that saved timestamp is older than ``ttl`` during a later load.
    Expiry is sliding from the last write (not absolute from creation) and is
    enforced lazily on load because ``Storage`` has no native TTL concept. Load
    hits do not refresh the timestamp; only a later successful save does.
    """
