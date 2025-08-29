"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Protocol

from pydantic import BaseModel

from .function import Function
from .message import Message, ModelMessage


class ChatModel(Protocol):
    async def send(
        self,
        input: Message,
        *,
        system: Message | None = None,
        messages: list[Message] | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
    ) -> ModelMessage: ...
