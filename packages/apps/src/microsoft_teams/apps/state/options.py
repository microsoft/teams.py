"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from microsoft_teams.common import Storage, StorageOptions


@dataclass(frozen=True)
class StateOptions:
    """Configuration for the per-turn state layer.

    Scope keys are namespaced under ``key_prefix``. Storage-specific behavior,
    including expiry, is configured through ``storage_options`` and enforced by
    the selected storage implementation.
    """

    storage: Optional[Storage[str, Any]] = None
    """Backing store for state blobs. When ``None`` the loader must be given one."""

    key_prefix: str = "ts"
    """Namespace prefix for scope keys (``{prefix}:conv:...`` / ``{prefix}:user:...``)."""

    storage_options: Optional[StorageOptions] = None
    """Optional settings passed to storage whenever a state scope is written."""
