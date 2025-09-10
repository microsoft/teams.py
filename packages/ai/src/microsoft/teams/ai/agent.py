"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable

from microsoft.teams.ai.plugin import AIPluginProtocol

from .ai_model import AIModel
from .chat_prompt import ChatPrompt, ChatSendResult
from .function import Function
from .memory import ListMemory, Memory
from .message import Message, SystemMessage


class Agent(ChatPrompt):
    """
    A stateful implementation of ChatPrompt. You can pass it memory which will persist
    through the existence of the Agent.
    """

    def __init__(
        self,
        model: AIModel,
        *,
        memory: Memory | None = None,
        functions: list[Function[Any]] | None = None,
        plugins: list[AIPluginProtocol] | None = None,
    ):
        super().__init__(model, functions=functions, plugins=plugins)
        self.memory = memory or ListMemory()

    async def send(
        self,
        input: str | Message,
        *,
        instructions: SystemMessage | None = None,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
    ) -> ChatSendResult:
        return await super().send(input, memory=memory or self.memory, instructions=instructions, on_chunk=on_chunk)
