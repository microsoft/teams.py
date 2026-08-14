"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from collections import OrderedDict
from dataclasses import dataclass
from time import monotonic
from typing import Dict, List, Optional, TypeVar

from .storage import Storage, StorageOptions

V = TypeVar("V")


@dataclass(frozen=True)
class LocalStorageOptions:
    max: Optional[int] = None
    """Maximum number of items in the storage"""


class LocalStorage(Storage[str, V]):
    """
    A key-value storage with optional size limit and LRU behavior.
    """

    @property
    def store(self) -> OrderedDict[str, V]:
        self._purge_expired()
        return self._store

    @property
    def options(self) -> LocalStorageOptions:
        return self._options

    @property
    def keys(self) -> List[str]:
        self._purge_expired()
        return list(self._store.keys())

    @property
    def size(self) -> int:
        self._purge_expired()
        return len(self._store)

    def __init__(
        self,
        data: Optional[Dict[str, V]] = None,
        options: Optional[LocalStorageOptions] = None,
    ):
        self._store = OrderedDict(data or {})
        self._expires_at: Dict[str, float] = {}
        self._options = options or LocalStorageOptions()

    def get(self, key: str) -> Optional[V]:
        if self._delete_if_expired(key) or key not in self._store:
            return None

        value = self._store.pop(key)
        self._store[key] = value
        return value

    async def async_get(self, key: str) -> Optional[V]:
        return self.get(key)

    def set(self, key: str, value: V) -> None:
        self._set(key, value)

    async def async_set(self, key: str, value: V) -> None:
        return self.set(key, value)

    def set_with_options(self, key: str, value: V, options: StorageOptions) -> None:
        self._set(key, value, options.ttl)

    async def async_set_with_options(self, key: str, value: V, options: StorageOptions) -> None:
        return self.set_with_options(key, value, options)

    def _set(self, key: str, value: V, ttl: Optional[int] = None) -> None:
        self._purge_expired()
        self._expires_at.pop(key, None)

        if key in self._store:
            del self._store[key]
        elif self._options.max and len(self._store) >= self._options.max:
            evicted_key, _ = self._store.popitem(last=False)
            self._expires_at.pop(evicted_key, None)

        self._store[key] = value
        if ttl is not None:
            self._expires_at[key] = monotonic() + ttl

    def delete(self, key: str) -> None:
        self._store.pop(key, None)
        self._expires_at.pop(key, None)

    async def async_delete(self, key: str) -> None:
        return self.delete(key)

    def _delete_if_expired(self, key: str) -> bool:
        expires_at = self._expires_at.get(key)
        if expires_at is None or monotonic() < expires_at:
            return False
        self.delete(key)
        return True

    def _purge_expired(self) -> None:
        now = monotonic()
        for key, expires_at in list(self._expires_at.items()):
            if key not in self._store or now >= expires_at:
                self.delete(key)
