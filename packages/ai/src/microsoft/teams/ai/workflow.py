"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel

from .chat_model import ChatModel
from .function import Function
from .memory import Memory
from .message import Message, ModelMessage, UserMessage

T = TypeVar("T", bound=BaseModel)


@dataclass
class WorkflowResult:
    response: ModelMessage
    workflow: "AgentWorkflow"


class AgentWorkflow:
    def __init__(self, model: ChatModel, *, functions: list[Function[Any]] | None = None):
        self.model = model
        self.functions: dict[str, Function[Any]] = {func.name: func for func in functions} if functions else {}

    def with_function(self, function: Function[T]) -> "AgentWorkflow":
        self.functions[function.name] = function
        return self

    async def send(self, input: str | Message, *, memory: Memory | None = None) -> WorkflowResult:
        if isinstance(input, str):
            input = UserMessage(content=input)

        response = await self.model.send(input, memory=memory, functions=self.functions if self.functions else None)

        return WorkflowResult(response=response, workflow=self)
