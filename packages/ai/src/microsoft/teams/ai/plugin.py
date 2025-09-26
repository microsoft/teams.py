"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import abstractmethod
from typing import Optional, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

from .function import Function
from .message import Message, ModelMessage, SystemMessage

T = TypeVar("T")


@runtime_checkable
class AIPluginProtocol(Protocol):
    """
    Protocol defining the interface for AI plugins.

    AI plugins provide hooks into the message processing pipeline,
    allowing for custom behavior before/after sending messages,
    function calls, and system instruction building.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique name of the plugin.

        Used for identification and debugging purposes.

        Returns:
            String identifier for this plugin
        """
        ...

    async def on_before_send(self, input: Message) -> Message | None:
        """
        Modify input before sending to model.

        Args:
            input: Original input message

        Returns:
            Modified message or None to keep original
        """
        ...

    async def on_after_send(self, response: ModelMessage) -> ModelMessage | None:
        """
        Modify response after receiving from model.

        Args:
            response: Original model response

        Returns:
            Modified response or None to keep original
        """
        ...

    async def on_before_function_call(self, function_name: str, args: Optional[BaseModel] = None) -> None:
        """
        Called before a function is executed.

        Args:
            function_name: Name of the function being called
            args: Validated function arguments, if any.
        """
        ...

    async def on_after_function_call(
        self, function_name: str, result: str, args: Optional[BaseModel] = None
    ) -> str | None:
        """
        Called after a function is executed.

        Args:
            function_name: Name of the function that was called
            args: Function arguments that were used, if any.
            result: Function execution result

        Returns:
            Modified result or None to keep original
        """
        ...

    async def on_build_functions(self, functions: list[Function[BaseModel]]) -> list[Function[BaseModel]] | None:
        """
        Modify the functions array passed to the model.

        Args:
            functions: Current list of available functions

        Returns:
            Modified function list or None to keep original
        """
        ...

    async def on_build_instructions(self, instructions: SystemMessage | None) -> SystemMessage | None:
        """
        Modify the system message before sending to model.

        Args:
            instructions: Current system instructions

        Returns:
            Modified instructions or None to keep original
        """
        ...


class BaseAIPlugin:
    """
    Base implementation of AIPlugin with no-op methods.

    Provides default implementations for all plugin hooks that return
    the original values unchanged. Extend this class and override only
    the hooks you need to customize.
    """

    def __init__(self, name: str):
        """
        Initialize base plugin with a name.

        Args:
            name: Unique identifier for this plugin
        """
        self._name = name

    @property
    def name(self) -> str:
        """
        Unique name of the plugin.

        Returns:
            String identifier for this plugin
        """
        return self._name

    async def on_before_send(self, input: Message) -> Message | None:
        """Modify input before sending to model."""
        return input

    async def on_after_send(self, response: ModelMessage) -> ModelMessage | None:
        """Modify response after receiving from model."""
        return response

    async def on_before_function_call(self, function_name: str, args: Optional[BaseModel] = None) -> None:
        """Called before a function is executed."""
        pass

    async def on_after_function_call(
        self, function_name: str, result: str, args: Optional[BaseModel] = None
    ) -> str | None:
        """Called after a function is executed."""
        return result

    async def on_build_functions(self, functions: list[Function[BaseModel]]) -> list[Function[BaseModel]] | None:
        """Modify the functions array passed to the model."""
        return functions

    async def on_build_instructions(self, instructions: SystemMessage | None) -> SystemMessage | None:
        """Modify the system message before sending to model."""
        return instructions
