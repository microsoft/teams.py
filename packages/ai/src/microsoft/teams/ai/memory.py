"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Protocol

from microsoft.teams.common.storage import ListLocalStorage, ListStorage

from .message import Message


class Memory(Protocol):
    """
    Protocol for conversation memory storage implementations.

    Memory stores and retrieves conversation messages, enabling persistent
    context across multiple interactions with AI models.
    """

    async def push(self, message: Message) -> None:
        """
        Add a message to memory.

        Args:
            message: The message to store (user, model, system, or function message)
        """
        ...

    async def get_all(self) -> list[Message]:
        """
        Get all messages from memory.

        Returns:
            List of all stored messages in chronological order
        """
        ...

    async def set_all(self, messages: list[Message]) -> None:
        """
        Replace all messages in memory with the provided list.

        Args:
            messages: New list of messages to store, replacing existing content
        """
        ...


class ListMemory:
    """
    Default implementation of Memory using list-based storage.

    Provides in-memory storage for conversation messages with optional
    persistent storage backend support.
    """

    def __init__(self, storage: Optional[ListStorage[Message]] = None):
        """
        Initialize list-based memory.

        Args:
            storage: Optional storage backend. Defaults to in-memory ListLocalStorage
        """
        self._storage = storage or ListLocalStorage[Message]()

    async def push(self, message: Message) -> None:
        """Add a message to the storage backend."""
        await self._storage.async_append(message)

    async def get_all(self) -> list[Message]:
        """Retrieve all messages from the storage backend."""
        return await self._storage.async_items()

    async def set_all(self, messages: list[Message]) -> None:
        """Replace all messages in the storage backend."""
        await self._storage.async_clear()
        for message in messages:
            await self._storage.async_append(message)
