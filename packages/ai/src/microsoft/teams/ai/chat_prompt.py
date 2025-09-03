"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypeVar

from pydantic import BaseModel

from .ai_model import AIModel
from .function import Function
from .memory import Memory
from .message import Message, ModelMessage, UserMessage

T = TypeVar("T", bound=BaseModel)


@dataclass
class ChatSendResult:
    response: ModelMessage


class ChatPrompt:
    def __init__(self, model: AIModel, *, functions: list[Function[Any]] | None = None):
        self.model = model
        self.functions: dict[str, Function[Any]] = {func.name: func for func in functions} if functions else {}

    def with_function(self, function: Function[T]) -> "ChatPrompt":
        self.functions[function.name] = function
        return self

    async def send(
        self,
        input: str | Message,
        *,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
    ) -> ChatSendResult:
        if isinstance(input, str):
            input = UserMessage(content=input)

        async def on_chunk_fn(chunk: str):
            if not on_chunk:
                return
            res = on_chunk(chunk)
            if inspect.isawaitable(res):
                await res

        response = await self.model.generate_text(
            input,
            memory=memory,
            functions=self.functions if self.functions else None,
            on_chunk=on_chunk_fn if on_chunk else None,
        )

        return ChatSendResult(response=response)
