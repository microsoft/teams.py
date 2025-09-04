"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import abstractmethod
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from .function import Function
from .message import Message, ModelMessage, SystemMessage

T = TypeVar("T")


@runtime_checkable
class AIPluginProtocol(Protocol):
    """Protocol defining the interface for AI plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the plugin."""
        ...

    async def on_before_send(self, input: Message) -> Message | None:
        """Modify input before sending to model."""
        ...

    async def on_after_send(self, response: ModelMessage) -> ModelMessage | None:
        """Modify response after receiving from model."""
        ...

    async def on_before_function_call(self, function_name: str, args: BaseModel) -> None:
        """Called before a function is executed."""
        ...

    async def on_after_function_call(self, function_name: str, args: BaseModel, result: str) -> str | None:
        """Called after a function is executed."""
        ...

    async def on_build_functions(self, functions: list[Function[BaseModel]]) -> list[Function[BaseModel]] | None:
        """Modify the functions array passed to the model."""
        ...

    async def on_build_system_message(self, system_message: SystemMessage | None) -> SystemMessage | None:
        """Modify the system message before sending to model."""
        ...


class BaseAIPlugin:
    """Base implementation of AIPlugin with no-op methods."""

    def __init__(self, name: str):
        self._name = name

    @property
    def name(self) -> str:
        """Unique name of the plugin."""
        return self._name

    async def on_before_send(self, input: Message) -> Message | None:
        """Modify input before sending to model."""
        return input

    async def on_after_send(self, response: ModelMessage) -> ModelMessage | None:
        """Modify response after receiving from model."""
        return response

    async def on_before_function_call(self, function_name: str, args: BaseModel) -> None:
        """Called before a function is executed."""
        pass

    async def on_after_function_call(self, function_name: str, args: BaseModel, result: str) -> str | None:
        """Called after a function is executed."""
        return result

    async def on_build_functions(self, functions: list[Function[BaseModel]]) -> list[Function[BaseModel]] | None:
        """Modify the functions array passed to the model."""
        return functions

    async def on_build_system_message(self, system_message: SystemMessage | None) -> SystemMessage | None:
        """Modify the system message before sending to model."""
        return system_message
