"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Awaitable, Callable, Self, TypeVar

from pydantic import BaseModel

from .ai_model import AIModel
from .function import Function, FunctionHandler
from .memory import Memory
from .message import Message, ModelMessage, SystemMessage, UserMessage
from .plugin import AIPluginProtocol

T = TypeVar("T", bound=BaseModel)


@dataclass
class ChatSendResult:
    response: ModelMessage


class ChatPrompt:
    def __init__(
        self,
        model: AIModel,
        *,
        functions: list[Function[Any]] | None = None,
        plugins: list[AIPluginProtocol] | None = None,
    ):
        self.model = model
        self.functions: dict[str, Function[Any]] = {func.name: func for func in functions} if functions else {}
        self.plugins: list[AIPluginProtocol] = plugins or []

    def with_function(self, function: Function[T]) -> Self:
        self.functions[function.name] = function
        return self

    def with_plugin(self, plugin: AIPluginProtocol) -> Self:
        """Add a plugin to the chat prompt."""
        self.plugins.append(plugin)
        return self

    async def send(
        self,
        input: str | Message,
        *,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
        instructions: SystemMessage | None = None,
    ) -> ChatSendResult:
        if isinstance(input, str):
            input = UserMessage(content=input)

        current_input = await self._run_before_send_hooks(input)
        current_system_message = await self._run_build_instructions_hooks(instructions)
        wrapped_functions = await self._build_wrapped_functions()

        async def on_chunk_fn(chunk: str):
            if not on_chunk:
                return
            res = on_chunk(chunk)
            if inspect.isawaitable(res):
                await res

        response = await self.model.generate_text(
            current_input,
            system=current_system_message,
            memory=memory,
            functions=wrapped_functions,
            on_chunk=on_chunk_fn if on_chunk else None,
        )

        current_response = await self._run_after_send_hooks(response)

        return ChatSendResult(response=current_response)

    def _wrap_function_handler(
        self, original_handler: FunctionHandler[BaseModel], function_name: str
    ) -> FunctionHandler[BaseModel]:
        """Wrap a function handler with plugin before/after hooks."""

        async def wrapped_handler(params: BaseModel) -> str:
            # Run before function call hooks
            for plugin in self.plugins:
                await plugin.on_before_function_call(function_name, params)

            # Call the original function (could be sync or async)
            result = original_handler(params)
            if isawaitable(result):
                result = await result

            # Run after function call hooks
            current_result = result
            for plugin in self.plugins:
                plugin_result = await plugin.on_after_function_call(function_name, params, current_result)
                if plugin_result is not None:
                    current_result = plugin_result

            return current_result

        return wrapped_handler

    async def _run_before_send_hooks(self, input: Message) -> Message:
        current_input = input
        for plugin in self.plugins:
            plugin_result = await plugin.on_before_send(current_input)
            if plugin_result is not None:
                current_input = plugin_result
        return current_input

    async def _run_build_instructions_hooks(self, instructions: SystemMessage | None) -> SystemMessage | None:
        current_instructions = instructions
        for plugin in self.plugins:
            plugin_result = await plugin.on_build_instructions(current_instructions)
            if plugin_result is not None:
                current_instructions = plugin_result
        return current_instructions

    async def _build_wrapped_functions(self) -> dict[str, Function[BaseModel]] | None:
        functions_list = list(self.functions.values()) if self.functions else []
        for plugin in self.plugins:
            plugin_result = await plugin.on_build_functions(functions_list)
            if plugin_result is not None:
                functions_list = plugin_result

        wrapped_functions: dict[str, Function[BaseModel]] | None = None
        wrapped_functions = {}
        for func in functions_list:
            wrapped_functions[func.name] = Function[BaseModel](
                name=func.name,
                description=func.description,
                parameter_schema=func.parameter_schema,
                handler=self._wrap_function_handler(func.handler, func.name),
            )

        return wrapped_functions

    async def _run_after_send_hooks(self, response: ModelMessage) -> ModelMessage:
        current_response = response
        for plugin in self.plugins:
            plugin_result = await plugin.on_after_send(current_response)
            if plugin_result is not None:
                current_response = plugin_result
        return current_response
