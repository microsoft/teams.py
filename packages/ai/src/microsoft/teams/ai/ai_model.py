"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Protocol

from pydantic import BaseModel

from .function import Function
from .memory import Memory
from .message import Message, ModelMessage, SystemMessage


class AIModel(Protocol):
    """
    Protocol defining the interface for AI models that can generate text responses.

    This protocol standardizes how different AI providers (OpenAI, Azure OpenAI, etc.)
    integrate with the Teams AI framework. Implementations should handle message
    processing, function calling, and optional streaming.
    """

    async def generate_text(
        self,
        input: Message,
        *,
        system: SystemMessage | None = None,
        memory: Memory | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
    ) -> ModelMessage:
        """
        Generate a text response from the AI model.

        Args:
            input: The input message to process (user, model, function, or system message)
            system: Optional system message to guide model behavior
            memory: Optional memory storage for conversation history
            functions: Optional dictionary of available functions the model can call
            on_chunk: Optional callback for streaming text chunks as they arrive

        Returns:
            ModelMessage containing the generated response, potentially with function calls

        Note:
            Implementations should handle function calling recursively - if the returned
            ModelMessage contains function_calls, they should be executed and the results
            fed back into the model for a final response.
        """
        ...
