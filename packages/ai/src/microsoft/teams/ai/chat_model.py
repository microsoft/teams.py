"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Protocol

from pydantic import BaseModel

from .function import Function
from .memory import Memory
from .message import Message, ModelMessage, SystemMessage


class ChatModel(Protocol):
    async def send(
        self,
        input: Message,
        *,
        system: SystemMessage | None = None,
        memory: Memory | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
    ) -> ModelMessage: ...
