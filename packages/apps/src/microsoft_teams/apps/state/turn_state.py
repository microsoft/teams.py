"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, MutableMapping
from typing import Any, Dict, Optional


class TurnStateSealedError(RuntimeError):
    """Raised when a sealed :class:`TurnState` is accessed after its turn ends."""


class TurnState(MutableMapping[str, Any]):
    """One state scope for a single turn.

    Behaves like a ``dict`` but adds two things the loader relies on:

    * **Dirty tracking** — the loader only writes a scope back when it was
      mutated, so an untouched scope costs nothing to "save".
    * **Sealing** — at the end of a turn the scope is sealed; any later access
      raises :class:`TurnStateSealedError`.

    **Values must be JSON-serializable.** Each scope is encoded with
    ``json.dumps`` when it is saved, so store only JSON-native types (``str``,
    ``int``, ``float``, ``bool``, ``None``, ``list``, ``dict``). A non-serializable
    value (e.g. a ``datetime`` or a custom object) is accepted on assignment but
    raises ``TypeError`` later, when the turn is saved.
    """

    def __init__(self, data: Optional[Mapping[str, Any]] = None) -> None:
        self._data: Dict[str, Any] = dict(data) if data else {}
        self._dirty = False
        self._sealed = False

    @property
    def is_dirty(self) -> bool:
        """Whether the scope has been mutated since it was loaded."""
        return self._dirty

    @property
    def is_empty(self) -> bool:
        """Whether the scope currently holds no keys."""
        return not self._data

    @property
    def is_sealed(self) -> bool:
        """Whether the scope has been sealed for the turn."""
        return self._sealed

    def seal(self) -> None:
        """Seal the scope; subsequent access raises :class:`TurnStateSealedError`."""
        self._sealed = True

    def to_dict(self) -> Dict[str, Any]:
        """Return a shallow copy of the raw contents (used for serialization).

        Intentionally does not check the seal: the loader serializes a scope just
        before sealing it, and callers should not reach for this directly.
        """
        return dict(self._data)

    def _ensure_active(self) -> None:
        if self._sealed:
            raise TurnStateSealedError("TurnState has been sealed and can no longer be accessed.")

    def __getitem__(self, key: str) -> Any:
        self._ensure_active()
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._ensure_active()
        self._data[key] = value
        self._dirty = True

    def __delitem__(self, key: str) -> None:
        self._ensure_active()
        del self._data[key]
        self._dirty = True

    def __iter__(self) -> Iterator[str]:
        self._ensure_active()
        # Snapshot so callers can mutate the scope while iterating (e.g. clear()).
        return iter(list(self._data))

    def __len__(self) -> int:
        return len(self._data)

    def __contains__(self, key: object) -> bool:
        self._ensure_active()
        return key in self._data

    def __repr__(self) -> str:
        status = "sealed" if self._sealed else ("dirty" if self._dirty else "clean")
        return f"TurnState({self._data!r}, {status})"
