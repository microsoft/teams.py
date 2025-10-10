"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, TypedDict, cast

from microsoft.teams.ai import (
    AIModel,
    Function,
    FunctionCall,
    FunctionMessage,
    ListMemory,
    Memory,
    Message,
    ModelMessage,
    SystemMessage,
    UserMessage,
)
from microsoft.teams.ai.function import FunctionHandler, FunctionHandlerWithNoParams
from microsoft.teams.openai.common import OpenAIBaseModel
from pydantic import BaseModel

from openai import NOT_GIVEN
from openai._streaming import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionChunk,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolUnionParam,
    ChatCompletionUserMessageParam,
)

from .function_utils import get_function_schema, parse_function_arguments


class _ToolCallData(TypedDict):
    """
    Internal structure for accumulating streaming tool call data.

    Used during streaming responses to build up function calls
    piece by piece as chunks arrive from the API.
    """

    id: str  # Function call ID
    name: str  # Function name
    arguments_str: str  # Accumulated JSON arguments string


@dataclass
class OpenAICompletionsAIModel(OpenAIBaseModel, AIModel):
    """
    OpenAI Chat Completions API implementation of AIModel.

    Uses the standard OpenAI Chat Completions API for text generation,
    supporting streaming, function calling, and conversation management.
    This is the traditional stateless approach where conversation history
    must be explicitly managed.
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
        Generate text using OpenAI Chat Completions API.

        Args:
            input: Input message to process
            system: Optional system message for context
            memory: Memory for conversation history
            functions: Available functions for the model to call
            on_chunk: Optional streaming callback for response chunks

        Returns:
            ModelMessage with generated content and/or function calls

        Note:
            Handles function calling recursively - if the model returns
            function calls, they are executed and results fed back for
            a final text response.
        """
        # Use default memory if none provided
        if memory is None:
            memory = ListMemory()

        # Execute any pending function calls first
        function_results = await self._execute_functions(input, functions)

        # Get conversation history from memory (make a copy to avoid modifying memory's internal state)
        messages = list(await memory.get_all())
        self.logger.debug(f"Retrieved {len(messages)} messages from memory, {len(function_results)} function results")

        # Push current input to memory
        await memory.push(input)

        # Push function results to memory and add to messages
        if function_results:
            # Add the original ModelMessage with function_calls to messages first
            messages.append(input)
            for result in function_results:
                await memory.push(result)
                messages.append(result)
            # Don't add input again at the end - Order matters here!
            input_to_send = None
        else:
            input_to_send = input

        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(input_to_send, system, messages)
        self.logger.debug(f"Converted to {len(openai_messages)} OpenAI messages")

        # Convert functions to OpenAI tools format if provided
        tools = self._convert_functions(functions) if functions else NOT_GIVEN

        self.logger.debug(f"Making Chat Completions API call (streaming: {bool(on_chunk)})")

        # Make OpenAI API call (with streaming if on_chunk provided)
        response = await self._client.chat.completions.create(
            model=self._model, messages=openai_messages, tools=tools, stream=bool(on_chunk)
        )

        # Convert response back to ModelMessage format
        if isinstance(response, AsyncStream):
            model_response = await self._handle_streaming_response(response, on_chunk)
        else:
            model_response = self._convert_response(response)

        # If response has function calls, recursively execute them
        if model_response.function_calls:
            self.logger.debug(
                f"Response has {len(model_response.function_calls)} function calls, executing recursively"
            )
            return await self.generate_text(model_response, system=system, memory=memory, functions=functions)

        # Push response to memory (only if not recursing)
        await memory.push(model_response)
        self.logger.debug("Chat Completions conversation completed, returning response")

        return model_response

    async def _execute_functions(
        self, input: Message, functions: dict[str, Function[BaseModel]] | None
    ) -> list[FunctionMessage]:
        """Execute any pending function calls in the input message."""
        function_results: list[FunctionMessage] = []

        if isinstance(input, ModelMessage) and input.function_calls:
            # Execute any pending function calls
            self.logger.debug(f"Executing {len(input.function_calls)} function calls")
            for call in input.function_calls:
                if functions and call.name in functions:
                    function = functions[call.name]
                    try:
                        # Parse arguments using utility function
                        parsed_args = parse_function_arguments(function, call.arguments)
                        if parsed_args:
                            # Handle both sync and async function handlers
                            handler = cast(FunctionHandler[BaseModel], function.handler)
                            result = handler(parsed_args)
                        else:
                            handler = cast(FunctionHandlerWithNoParams, function.handler)
                            result = handler()

                        if inspect.isawaitable(result):
                            fn_res = await result
                        else:
                            fn_res = result

                        # Create function result message
                        function_results.append(FunctionMessage(content=fn_res, function_id=call.id))
                    except Exception as e:
                        self.logger.error(e)
                        # Handle function execution errors
                        function_results.append(
                            FunctionMessage(content=f"Function execution failed: {str(e)}", function_id=call.id)
                        )

        return function_results

    async def _handle_streaming_response(
        self, stream: AsyncStream[ChatCompletionChunk], on_chunk: Callable[[str], Awaitable[None]] | None
    ) -> ModelMessage:
        """Handle streaming OpenAI response and accumulate into ModelMessage."""
        # Initialize accumulation structures
        content = ""
        tool_calls_data: list[_ToolCallData] = []  # List of dict to accumulate tool call data

        async for chunk in stream:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Handle content streaming
            if delta.content:
                content += delta.content
                if on_chunk:
                    await on_chunk(delta.content)

            # Handle tool calls streaming
            if delta.tool_calls:
                for call_delta in delta.tool_calls:
                    # Ensure we have enough slots for this index
                    while len(tool_calls_data) <= call_delta.index:
                        tool_calls_data.append({"id": "", "name": "", "arguments_str": ""})

                    # Accumulate call data
                    if call_delta.id:
                        tool_calls_data[call_delta.index]["id"] += call_delta.id

                    if call_delta.function:
                        if call_delta.function.name:
                            tool_calls_data[call_delta.index]["name"] += call_delta.function.name

                        if call_delta.function.arguments:
                            tool_calls_data[call_delta.index]["arguments_str"] += call_delta.function.arguments

        # Convert accumulated tool calls to FunctionCall objects
        function_calls: list[FunctionCall] = []
        for call_data in tool_calls_data:
            try:
                arguments: dict[str, Any] = json.loads(call_data["arguments_str"]) if call_data["arguments_str"] else {}
            except json.JSONDecodeError:
                arguments = {}

            function_calls.append(FunctionCall(id=call_data["id"], name=call_data["name"], arguments=arguments))

        return ModelMessage(
            content=content if content else None, function_calls=function_calls if function_calls else None
        )

    def _convert_messages(
        self, input: Message | None, system: SystemMessage | None, messages: list[Message] | None
    ) -> list[ChatCompletionMessageParam]:
        openai_messages: list[ChatCompletionMessageParam] = []

        # Add system message if provided
        if system and system.content:
            openai_messages.append(ChatCompletionSystemMessageParam(content=system.content, role="system"))

        # Add conversation history if provided
        if messages:
            for msg in messages:
                openai_messages.append(self._convert_message_to_openai_format(msg))

        # Add the input message (if provided)
        if input:
            openai_messages.append(self._convert_message_to_openai_format(input))

        return openai_messages

    def _convert_message_to_openai_format(self, message: Message) -> ChatCompletionMessageParam:
        if isinstance(
            message,
            UserMessage,
        ):
            return ChatCompletionUserMessageParam(role=message.role, content=message.content)
        if isinstance(message, SystemMessage):
            return ChatCompletionSystemMessageParam(role=message.role, content=message.content)

        elif isinstance(message, FunctionMessage):
            return ChatCompletionToolMessageParam(
                role="tool",
                content=message.content or [],
                tool_call_id=message.function_id,
            )
        elif isinstance(message, ModelMessage):  # pyright: ignore [reportUnnecessaryIsInstance]
            if message.function_calls:
                tool_calls = [
                    ChatCompletionMessageFunctionToolCallParam(
                        id=call.id,
                        function={"name": call.name, "arguments": json.dumps(call.arguments)},
                        type="function",
                    )
                    for call in message.function_calls
                ]
            else:
                # we need to do this cast because Completions expects tool_calls to be >= 1,
                # but the type is not Optional
                tool_calls = cast(list[ChatCompletionMessageFunctionToolCallParam], None)
            return ChatCompletionAssistantMessageParam(role="assistant", content=message.content, tool_calls=tool_calls)
        else:
            raise Exception(f"Message {message.role} not supported")

    def _convert_functions(self, functions: dict[str, Function[BaseModel]]) -> list[ChatCompletionToolUnionParam]:
        function_values = functions.values()
        if len(function_values) == 0:
            return []
        return [
            {
                "type": "function",
                "function": {
                    "name": func.name,
                    "description": func.description,
                    "parameters": get_function_schema(func),
                },
            }
            for func in function_values
        ]

    def _convert_response(self, response: ChatCompletion) -> ModelMessage:
        message = response.choices[0].message

        function_calls = None
        if message.tool_calls:
            function_calls = [
                FunctionCall(name=call.function.name, id=call.id, arguments=json.loads(call.function.arguments))
                for call in message.tool_calls
                if isinstance(call, ChatCompletionMessageFunctionToolCall)
            ]

        return ModelMessage(content=message.content, function_calls=function_calls)
