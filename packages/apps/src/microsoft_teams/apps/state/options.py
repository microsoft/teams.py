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
    """Optional time-to-live, in **seconds**, applied by the loader on load."""
