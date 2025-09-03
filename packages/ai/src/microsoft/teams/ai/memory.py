"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Protocol

from microsoft.teams.common.storage import ListLocalStorage, ListStorage

from .message import Message


class Memory(Protocol):
    async def push(self, message: Message) -> None:
        """Add a message to memory"""
        ...

    async def get_all(self) -> list[Message]:
        """Get all messages from memory"""
        ...


class ListMemory:
    def __init__(self, storage: Optional[ListStorage[Message]] = None):
        self._storage = storage or ListLocalStorage[Message]()

    async def push(self, message: Message) -> None:
        await self._storage.async_append(message)

    async def get_all(self) -> list[Message]:
        return await self._storage.async_items()
