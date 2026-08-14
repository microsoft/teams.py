"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Generic, List, Optional, TypeVar

K = TypeVar("K")
V = TypeVar("V")


@dataclass(frozen=True)
class StorageOptions:
    """Options applied when writing a value to storage."""

    ttl: Optional[int] = None
    """Optional time-to-live in seconds after the value is written."""


class Storage(Generic[K, V], ABC):
    """A storage container that can get/set/delete items by a unique key."""

    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        """Synchronously get a value by key."""
        pass

    @abstractmethod
    async def async_get(self, key: K) -> Optional[V]:
        """Asynchronously get a value by key."""
        pass

    @abstractmethod
    def set(self, key: K, value: V) -> None:
        """Synchronously set a value by key."""
        pass

    @abstractmethod
    async def async_set(self, key: K, value: V) -> None:
        """Asynchronously set a value by key."""
        pass

    def set_with_options(self, key: K, value: V, options: StorageOptions) -> None:
        """Synchronously set a value with storage-specific write options.

        Existing storage implementations inherit this method. Writes without
        effective options delegate to :meth:`set`; implementations that support
        TTL should override it.
        """
        if options.ttl is not None:
            raise NotImplementedError(f"{type(self).__name__} does not support TTL")
        self.set(key, value)

    async def async_set_with_options(self, key: K, value: V, options: StorageOptions) -> None:
        """Asynchronously set a value with storage-specific write options.

        Existing storage implementations inherit this method. Writes without
        effective options delegate to :meth:`async_set`; implementations that
        support TTL should override it.
        """
        if options.ttl is not None:
            raise NotImplementedError(f"{type(self).__name__} does not support TTL")
        await self.async_set(key, value)

    @abstractmethod
    def delete(self, key: K) -> None:
        """Synchronously delete a value by key."""
        pass

    @abstractmethod
    async def async_delete(self, key: K) -> None:
        """Asynchronously delete a value by key."""
        pass


class ListStorage(Storage[int, V], ABC):
    """A list storage container that can store/query iterable data."""

    @abstractmethod
    def append(self, value: V) -> None:
        """Synchronously append a value to the list."""
        pass

    @abstractmethod
    async def async_append(self, value: V) -> None:
        """Asynchronously append a value to the list."""
        pass

    @abstractmethod
    def pop(self) -> Optional[V]:
        """Synchronously remove and return the last value."""
        pass

    @abstractmethod
    async def async_pop(self) -> Optional[V]:
        """Asynchronously remove and return the last value."""
        pass

    @abstractmethod
    def items(self) -> List[V]:
        """Synchronously return all items as a list."""
        pass

    @abstractmethod
    async def async_items(self) -> List[V]:
        """Asynchronously return all items as a list."""
        pass

    @abstractmethod
    def length(self) -> int:
        """Return the number of items."""
        pass

    @abstractmethod
    async def async_length(self) -> int:
        """Return the number of items."""
        pass

    @abstractmethod
    def filter(self, predicate: Callable[[V, int], bool]) -> List[V]:
        """Synchronously filter items using predicate."""
        pass

    @abstractmethod
    async def async_filter(self, predicate: Callable[[V, int], bool]) -> List[V]:
        """Asynchronously filter items using predicate."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Synchronously clear all items from the list."""
        pass

    @abstractmethod
    async def async_clear(self) -> None:
        """Asynchronously clear all items from the list."""
        pass
