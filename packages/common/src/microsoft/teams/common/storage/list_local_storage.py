"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Callable, List, Optional, TypeVar

from .storage import ListStorage

V = TypeVar("V")


class ListLocalStorage(ListStorage[V]):
    """A local storage implementation for a list of items."""

    def __init__(self, items: Optional[List[V]] = None):
        self._items = items or []

    def get(self, key: int) -> Optional[V]:
        if key < 0 or key >= len(self._items):
            return None
        return self._items[key]

    async def async_get(self, key: int) -> Optional[V]:
        return self.get(key)

    def set(self, key: int, value: V) -> None:
        self._items[key] = value

    async def async_set(self, key: int, value: V) -> None:
        return self.set(key, value)

    def delete(self, key: int) -> None:
        del self._items[key]

    async def async_delete(self, key: int) -> None:
        return self.delete(key)

    def append(self, value: V) -> None:
        return self._items.append(value)

    async def async_append(self, value: V) -> None:
        return self.append(value)

    def pop(self) -> Optional[V]:
        return self._items.pop()

    async def async_pop(self) -> Optional[V]:
        return self.pop()

    def items(self) -> List[V]:
        return self._items

    async def async_items(self) -> List[V]:
        return self.items()

    def length(self) -> int:
        return len(self._items)

    async def async_length(self) -> int:
        return self.length()

    def filter(self, predicate: Callable[[V, int], bool]) -> List[V]:
        return [item for i, item in enumerate(self._items) if predicate(item, i)]

    async def async_filter(self, predicate: Callable[[V, int], bool]) -> List[V]:
        return self.filter(predicate)
