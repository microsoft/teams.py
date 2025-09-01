"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, Awaitable, Callable, TypeVar

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

    def with_function(self, function: Function[T]) -> "ChatPrompt":
        self.functions[function.name] = function
        return self

    def with_plugin(self, plugin: AIPluginProtocol) -> "ChatPrompt":
        """Add a plugin to the chat prompt."""
        self.plugins.append(plugin)
        return self

    async def send(
        self,
        input: str | Message,
        *,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
        system_message: SystemMessage | None = None,
    ) -> ChatSendResult:
        if isinstance(input, str):
            input = UserMessage(content=input)

        # Allow plugins to modify the input before sending
        current_input = input
        for plugin in self.plugins:
            plugin_result = await plugin.on_before_send(current_input)
            if plugin_result is not None:
                current_input = plugin_result

        # Allow plugins to modify the system message
        current_system_message = system_message
        for plugin in self.plugins:
            plugin_result = await plugin.on_build_system_message(current_system_message)
            if plugin_result is not None:
                current_system_message = plugin_result

        # Wrap functions with plugin hooks
        wrapped_functions: dict[str, Function[BaseModel]] | None = None
        if self.functions:
            wrapped_functions = {}
            for name, func in self.functions.items():
                wrapped_functions[name] = Function[BaseModel](
                    name=func.name,
                    description=func.description,
                    parameter_schema=func.parameter_schema,
                    handler=self._wrap_function_handler(func.handler, name),
                )

        # Allow plugins to modify the functions before sending to model
        if wrapped_functions:
            functions_list = list(wrapped_functions.values())
            for plugin in self.plugins:
                plugin_result = await plugin.on_build_functions(functions_list)
                if plugin_result is not None:
                    functions_list = plugin_result

            # Convert back to dict for model
            wrapped_functions = {func.name: func for func in functions_list}

        async def on_chunk_fn(chunk: str):
            if not on_chunk:
                return
            res = on_chunk(chunk)
            if inspect.isawaitable(res):
                await res

        response = await self.model.generate_text(
            current_input, memory=memory, functions=wrapped_functions, on_chunk=on_chunk_fn if on_chunk else None
        )

        # Allow plugins to modify the response after receiving
        current_response = response
        for plugin in self.plugins:
            plugin_result = await plugin.on_after_send(current_response)
            if plugin_result is not None:
                current_response = plugin_result

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
