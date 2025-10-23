"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from dataclasses import dataclass
from inspect import isawaitable
from logging import Logger
from typing import Any, Awaitable, Callable, Dict, Optional, Self, TypeVar, Union, cast, overload

from microsoft.teams.common.logging import ConsoleLogger
from pydantic import BaseModel

from .ai_model import AIModel
from .function import Function, FunctionHandler, FunctionHandlers, FunctionHandlerWithNoParams
from .memory import Memory
from .message import DeferredMessage, FunctionMessage, Message, ModelMessage, SystemMessage, UserMessage
from .plugin import AIPluginProtocol

T = TypeVar("T", bound=BaseModel)


@dataclass
class ChatSendResult:
    """
    Result of sending a message through ChatPrompt.

    Contains the final response from the AI model after all function
    calls and plugin processing have been completed.
    """

    response: ModelMessage | None  # Final model response after processing
    is_deferred: bool = False


class ChatPrompt:
    """
    Core class for interacting with AI models through a prompt-based interface.

    Handles message processing, function calling, and plugin execution.
    Provides a flexible framework for building AI-powered applications.
    """

    def __init__(
        self,
        model: AIModel,
        *,
        functions: list[Function[Any]] | None = None,
        plugins: list[AIPluginProtocol] | None = None,
        memory: Memory | None = None,
        logger: Logger | None = None,
        instructions: str | SystemMessage | None = None,
    ):
        """
        Initialize ChatPrompt with model and optional functions/plugins.

        Args:
            model: AI model implementation for text generation
            functions: Optional list of functions the model can call
            plugins: Optional list of plugins for extending functionality
            memory: Optional memory for conversation context and deferred state
            logger: Optional logger for debugging and monitoring
            instructions: Optional default system instructions for the model
        """
        self.model = model
        self.functions: dict[str, Function[Any]] = {func.name: func for func in functions} if functions else {}
        self.plugins: list[AIPluginProtocol] = plugins or []
        self.memory = memory
        self.logger = logger or ConsoleLogger().create_logger("@teams/ai/chat_prompt")
        self.instructions = instructions

    @overload
    def with_function(self, function: Function[T]) -> Self: ...

    @overload
    def with_function(
        self,
        *,
        name: str,
        description: str,
        parameter_schema: Union[type[T], Dict[str, Any]],
        handler: FunctionHandlers,
    ) -> Self: ...

    @overload
    def with_function(
        self,
        *,
        name: str,
        description: str,
        handler: FunctionHandlerWithNoParams,
    ) -> Self: ...

    def with_function(
        self,
        function: Function[T] | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        parameter_schema: Union[type[T], Dict[str, Any], None] = None,
        handler: FunctionHandlers | None = None,
    ) -> Self:
        """
        Add a function to the available functions for this prompt.

        Can be called in three ways:
        1. with_function(function=Function(...))
        2. with_function(name=..., description=..., parameter_schema=..., handler=...)
        3. with_function(name=..., description=..., handler=...) - for functions with no parameters

        Args:
            function: Function object to add (first overload)
            name: Function name (second and third overload)
            description: Function description (second and third overload)
            parameter_schema: Function parameter schema (second overload, optional)
            handler: Function handler (second and third overload)

        Returns:
            Self for method chaining
        """
        if function is not None:
            self.functions[function.name] = function
        else:
            if name is None or description is None or handler is None:
                raise ValueError("When not providing a Function object, name, description, and handler are required")
            func = Function[T](
                name=name,
                description=description,
                parameter_schema=parameter_schema,
                handler=handler,
            )
            self.functions[func.name] = func
        return self

    def with_plugin(self, plugin: AIPluginProtocol) -> Self:
        """
        Add a plugin to the chat prompt.

        Args:
            plugin: Plugin to add for extending functionality

        Returns:
            Self for method chaining
        """
        self.plugins.append(plugin)
        return self

    async def requires_resuming(self) -> bool:
        """
        Check if there are any deferred functions that need resuming.

        Returns:
            True if there are DeferredMessage objects in memory that need resuming
        """
        if not self.memory:
            return False

        messages = await self.memory.get_all()
        return any(isinstance(msg, DeferredMessage) for msg in messages)

    async def resolve_deferred(self, activity: Any) -> list[str]:
        """
        Resolve deferred functions with the provided activity input.

        Only attempts to resolve deferred functions whose resumers can handle
        the provided activity type (determined by can_handle method).

        Args:
            activity: Activity data to use for resolving deferred functions

        Returns:
            List of resolution results from successfully resolved functions
        """
        if not self.memory:
            return []

        messages = await self.memory.get_all()
        deferred_messages = [msg for msg in messages if isinstance(msg, DeferredMessage)]

        if not deferred_messages:
            return []

        results: list[str] = []
        updated_messages = messages.copy()  # Work with a copy

        for i, msg in enumerate(updated_messages):
            if not isinstance(msg, DeferredMessage):
                continue

            # Try plugins first, then fall back to built-in resumer
            result = await self._try_resolve_with_plugins(msg, activity)
            if result is None:
                result = await self._try_resolve_with_builtin_resumer(msg, activity)

            if result is not None:
                updated_messages[i] = FunctionMessage(content=result, function_id=msg.function_id)
                results.append(result)

        # Update memory with resolved messages
        if results:  # Only update if we actually resolved something
            await self.memory.set_all(updated_messages)

        return results

    async def _try_resolve_with_plugins(self, msg: DeferredMessage, activity: Any) -> str | None:
        """
        Try to resolve a deferred message using plugins.

        Args:
            msg: The deferred message to resolve
            activity: Activity data for resolution

        Returns:
            Result string if a plugin handled it, None otherwise
        """
        for plugin in self.plugins:
            result = await plugin.on_resume(msg.function_name, activity, msg.deferred_result.state)
            if result is not None:
                return result
        return None

    async def _try_resolve_with_builtin_resumer(self, msg: DeferredMessage, activity: Any) -> str | None:
        """
        Try to resolve a deferred message using the built-in resumer.

        Args:
            msg: The deferred message to resolve
            activity: Activity data for resolution

        Returns:
            Result string if resolved successfully, None if skipped, raises on error
        """
        resumer_name = msg.function_name
        associated_func = self.functions.get(resumer_name)

        if not associated_func or associated_func.resumer is None:
            raise ValueError(f"Expected a resumer for {resumer_name} but chat prompt was not set up with one")

        # Check if the resumer can handle this type of activity
        if not associated_func.resumer.can_handle(activity):
            return None  # Skip this deferred function

        try:
            # Call the resumer with the activity and saved state
            result = associated_func.resumer(activity, msg.deferred_result.state)
            if isawaitable(result):
                result = await result
            return result

        except Exception as e:
            # Return error message instead of raising
            return f"Error resolving {resumer_name}: {str(e)}"

    async def resume(self, activity: Any) -> ChatSendResult:
        """
        Resume deferred functions with the provided activity input.

        If all deferred functions are resolved, automatically continues with
        normal chat processing using the activity text as input.

        Args:
            activity: Activity data to use for resolving deferred functions

        Returns:
            ChatSendResult - either indicating still deferred or containing the chat response
        """
        await self.resolve_deferred(activity)

        # If there are still deferred functions pending, return early
        if await self.requires_resuming():
            return ChatSendResult(response=None, is_deferred=True)

        return await self.send(input=None)

    async def send(
        self,
        input: str | Message | None,
        *,
        memory: Memory | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | Callable[[str], None] | None = None,
        instructions: str | SystemMessage | None = None,
    ) -> ChatSendResult:
        """
        Send a message to the AI model and get a response.

        Args:
            input: Message to send (string will be converted to UserMessage)
            memory: Optional memory for conversation context
            on_chunk: Optional callback for streaming response chunks
            instructions: Optional system message to guide model behavior

        Returns:
            ChatSendResult containing the final model response

        """
        if isinstance(input, str):
            input = UserMessage(content=input)

        # Use constructor instructions as default if none provided
        if instructions is None:
            instructions = self.instructions

        # Convert string instructions to SystemMessage
        if isinstance(instructions, str):
            instructions = SystemMessage(content=instructions)

        if input is not None:
            current_input = await self._run_before_send_hooks(input)
        else:
            current_input = None
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
            memory=memory or self.memory,
            functions=wrapped_functions,
            on_chunk=on_chunk_fn if on_chunk else None,
        )
        if isinstance(response, list):
            return ChatSendResult(response=None, is_deferred=True)

        current_response = await self._run_after_send_hooks(response)

        return ChatSendResult(response=current_response)

    def _wrap_function_handler(self, original_handler: FunctionHandlers, function_name: str) -> FunctionHandlers:
        """
        Wrap a function handler with plugin before/after hooks.

        Creates a new handler that executes plugin hooks before and after
        the original function, allowing plugins to modify parameters and results.

        Args:
            original_handler: The original function handler to wrap
            function_name: Name of the function for plugin identification

        Returns:
            Wrapped handler that includes plugin hook execution
        """

        async def wrapped_handler(params: Optional[BaseModel]) -> str:
            # Run before function call hooks
            for plugin in self.plugins:
                await plugin.on_before_function_call(function_name, params)

            if params:
                # Call the original function with params (could be sync or async)
                casted_handler = cast(FunctionHandler[BaseModel], original_handler)
                result = casted_handler(params)
                if isawaitable(result):
                    result = await result
            else:
                # Function with no parameters case
                casted_handler = cast(FunctionHandlerWithNoParams, original_handler)
                result = casted_handler()
                if isawaitable(result):
                    result = await result

            # Run after function call hooks
            current_result = result
            for plugin in self.plugins:
                plugin_result = await plugin.on_after_function_call(function_name, current_result, params)
                if plugin_result is not None:
                    current_result = plugin_result

            return current_result

        return wrapped_handler

    async def _run_before_send_hooks(self, input: Message) -> Message:
        """
        Execute before-send hooks from all plugins.

        Args:
            input: Original input message

        Returns:
            Modified input message after plugin processing
        """
        current_input = input
        for plugin in self.plugins:
            plugin_result = await plugin.on_before_send(current_input)
            if plugin_result is not None:
                current_input = plugin_result
        return current_input

    async def _run_build_instructions_hooks(self, instructions: SystemMessage | None) -> SystemMessage | None:
        """
        Execute build-instructions hooks from all plugins.

        Args:
            instructions: Original system instructions

        Returns:
            Modified system instructions after plugin processing
        """
        current_instructions = instructions
        for plugin in self.plugins:
            plugin_result = await plugin.on_build_instructions(current_instructions)
            if plugin_result is not None:
                current_instructions = plugin_result
        return current_instructions

    async def _build_wrapped_functions(self) -> dict[str, Function[BaseModel]] | None:
        """
        Build function dictionary with plugin modifications and handler wrapping.

        Returns:
            Dictionary of functions with wrapped handlers, or None if no functions
        """
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
                handler=self._wrap_function_handler(cast(FunctionHandler[BaseModel], func.handler), func.name)
                if func.resumer is None
                else func.handler,
            )

        return wrapped_functions

    async def _run_after_send_hooks(self, response: ModelMessage) -> ModelMessage:
        """
        Execute after-send hooks from all plugins.

        Args:
            response: Original model response

        Returns:
            Modified response after plugin processing
        """
        current_response = response
        for plugin in self.plugins:
            plugin_result = await plugin.on_after_send(current_response)
            if plugin_result is not None:
                current_response = plugin_result
        return current_response
