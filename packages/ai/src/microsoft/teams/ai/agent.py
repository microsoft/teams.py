"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable

from .ai_model import AIModel
from .chat_prompt import ChatPrompt, ChatSendResult
from .function import Function
from .memory import Memory
from .message import Message


class Agent(ChatPrompt):
    def __init__(self, model: AIModel, *, memory: Memory | None = None, functions: list[Function[Any]] | None = None):
        super().__init__(model, functions=functions)
        self.memory = memory

    async def send(
        self,
        input: str | Message,
        *,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
    ) -> ChatSendResult:
        return await super().send(input, memory=memory or self.memory, on_chunk=on_chunk)
