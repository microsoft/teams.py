"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, Optional, TypeVar

from pydantic import BaseModel, Field

from .storage import Storage

V = TypeVar("V")


class LocalStorageOptions(BaseModel):
    max: Optional[int] = Field(default=None, frozen=True)


class LocalStorage(Storage[str, V]):
    """A key-value storage with optional size limit and LRU behavior.

    When max is set, implements LRU (Least Recently Used) behavior.
    """

    @property
    def store(self) -> OrderedDict[str, V]:
        return self._store

    @property
    def options(self) -> LocalStorageOptions:
        return self._options

    @property
    def keys(self) -> List[str]:
        return list(self._store.keys())

    @property
    def size(self) -> int:
        return len(self._store)

    def __init__(
        self,
        data: Optional[Dict[str, V]] = None,
        options: Optional[LocalStorageOptions] = None,
    ):
        self._store = OrderedDict(data or {})
        self._options = options or LocalStorageOptions()

    def get(self, key: str) -> Optional[V]:
        if key not in self._store:
            return None

        value = self._store.pop(key)
        self._store[key] = value
        return value

    async def async_get(self, key: str) -> Optional[V]:
        return self.get(key)

    def set(self, key: str, value: V) -> None:
        if key in self._store:
            del self._store[key]
        elif self._options.max and len(self._store) >= self._options.max:
            self._store.popitem(last=False)

        self._store[key] = value

    async def async_set(self, key: str, value: V) -> None:
        return self.set(key, value)

    def delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]

    async def async_delete(self, key: str) -> None:
        return self.delete(key)
