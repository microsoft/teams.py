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
    A stateful implementation of ChatPrompt with persistent memory.

    Agent extends ChatPrompt by providing default memory management,
    making it easier to maintain conversation context across multiple
    interactions without manually passing memory each time.
    """

    def __init__(
        self,
        model: AIModel,
        *,
        memory: Memory | None = None,
        functions: list[Function[Any]] | None = None,
        plugins: list[AIPluginProtocol] | None = None,
    ):
        """
        Initialize Agent with model and persistent memory.

        Args:
            model: AI model implementation for text generation
            memory: Memory for conversation persistence. Defaults to InMemory ListMemory
            functions: Optional list of functions the model can call
            plugins: Optional list of plugins for extending functionality
        """
        super().__init__(model, functions=functions, plugins=plugins)
        self.memory = memory or ListMemory()

    async def send(
        self,
        input: str | Message,
        *,
        instructions: str | SystemMessage | None = None,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
    ) -> ChatSendResult:
        """
        Send a message using the agent's persistent memory.

        Args:
            input: Message to send (string will be converted to UserMessage)
            instructions: Optional system message to guide model behavior
            memory: Optional memory override. Defaults to agent's persistent memory
            on_chunk: Optional callback for streaming response chunks

        Returns:
            ChatSendResult containing the final model response

        Note:
            If no memory is provided, uses the agent's default memory,
            making conversation state persistent across calls.
        """
        return await super().send(input, memory=memory or self.memory, instructions=instructions, on_chunk=on_chunk)
