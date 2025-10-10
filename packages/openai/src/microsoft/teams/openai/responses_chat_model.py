"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
import json
from dataclasses import dataclass
from typing import Awaitable, Callable, cast

from microsoft.teams.ai import (
    AIModel,
    Function,
    FunctionCall,
    FunctionHandler,
    FunctionHandlerWithNoParams,
    FunctionMessage,
    ListMemory,
    Memory,
    Message,
    ModelMessage,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel

from openai import NOT_GIVEN
from openai.lib._pydantic import (
    _ensure_strict_json_schema,  # pyright: ignore [reportPrivateUsage]
    to_strict_json_schema,
)
from openai.types.responses import (
    EasyInputMessageParam,
    FunctionToolParam,
    Response,
    ResponseFunctionToolCall,
    ResponseFunctionToolCallParam,
    ResponseInputParam,
    ToolParam,
)

from .common import OpenAIBaseModel
from .function_utils import get_function_schema, parse_function_arguments


@dataclass
class OpenAIResponsesAIModel(OpenAIBaseModel, AIModel):
    """
    OpenAI Responses API chat model implementation.

    The Responses API is stateful and manages conversation context automatically,
    making it simpler for complex multi-turn conversations with tools.
    Supports both stateful (recommended) and stateless modes.
    """

    stateful: bool = True  # Use stateful mode (recommended) or stateless mode

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
        Generate text using OpenAI Responses API.

        Args:
            input: Input message to process
            system: Optional system message for context
            memory: Memory for conversation history (managed differently in stateful mode)
            functions: Available functions for the model to call
            on_chunk: Optional streaming callback (limited support in Responses API)

        Returns:
            ModelMessage with generated content and/or function calls

        Note:
            In stateful mode, OpenAI manages conversation context automatically.
            In stateless mode, behaves more like traditional Chat Completions.
        """
        # Use default memory if none provided
        if memory is None:
            memory = ListMemory()

        # Execute any pending function calls first
        function_results = await self._execute_functions(input, functions)

        if self.stateful:
            return await self._send_stateful(input, system, memory, functions, on_chunk, function_results)
        else:
            return await self._send_stateless(input, system, memory, functions, on_chunk, function_results)

    async def _send_stateful(
        self,
        input: Message,
        system: SystemMessage | None,
        memory: Memory,
        functions: dict[str, Function[BaseModel]] | None,
        on_chunk: Callable[[str], Awaitable[None]] | None,
        function_results: list[FunctionMessage],
    ) -> ModelMessage:
        """Handle stateful conversation using OpenAI Responses API state management."""
        # Get response IDs from memory - OpenAI manages conversation state
        messages = list(await memory.get_all())

        # Extract previous response ID from memory - look for ModelMessage with ID
        previous_response_id = None
        for msg in reversed(messages):
            if isinstance(msg, ModelMessage) and msg.id:
                previous_response_id = msg.id
                break
        self.logger.debug(f"Found previous response ID: {previous_response_id}")
        if function_results:
            for result in function_results:
                await memory.push(result)
                messages.append(result)

        # Convert to Responses API format - just the current input as string
        responses_input = self._convert_to_responses_format(input, None, messages)
        # Convert functions to tools format
        tools = self._convert_functions_to_tools(functions) if functions else NOT_GIVEN

        self.logger.debug(f"Making Responses API call with input type: {type(input).__name__}")

        # Make OpenAI Responses API call
        response = await self._client.responses.create(
            model=self._model,
            input=responses_input,
            instructions=system.content if system and system.content else None,
            tools=tools,
            previous_response_id=previous_response_id,
        )

        self.logger.debug(f"Response API returned: {type(response)}")
        self.logger.debug(f"Response has content: {hasattr(response, 'content')}")
        self.logger.debug(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

        # Convert response to ModelMessage format
        model_response = self._convert_from_responses_format(response)

        # Store response ID in the ModelMessage for next call
        if hasattr(response, "id"):
            model_response.id = response.id

        # In stateful mode, replace memory with just the current response for next call
        await memory.set_all([model_response])

        # If response has function calls, recursively execute them
        if model_response.function_calls:
            self.logger.debug(
                f"Response has {len(model_response.function_calls)} function calls, executing recursively"
            )
            return await self.generate_text(
                model_response, system=system, memory=memory, functions=functions, on_chunk=on_chunk
            )

        self.logger.debug("Stateful Responses API conversation completed")
        self.logger.debug(model_response)
        return model_response

    async def _send_stateless(
        self,
        input: Message,
        system: SystemMessage | None,
        memory: Memory,
        functions: dict[str, Function[BaseModel]] | None,
        on_chunk: Callable[[str], Awaitable[None]] | None,
        function_results: list[FunctionMessage],
    ) -> ModelMessage:
        """Handle stateless conversation using standard OpenAI API pattern."""
        # Get conversation history from memory (make a copy to avoid modifying memory's internal state)
        messages = list(await memory.get_all())
        self.logger.debug(f"Retrieved {len(messages)} messages from memory")

        # Push current input to memory
        await memory.push(input)
        messages.append(input)

        # Push function results to memory and add to messages
        if function_results:
            for result in function_results:
                await memory.push(result)
                messages.append(result)

        # Convert to Responses API format - just the current input as string
        responses_input = self._convert_to_responses_format(input, None, messages)

        # Convert functions to tools format
        tools = self._convert_functions_to_tools(functions) if functions else NOT_GIVEN

        self.logger.debug(f"Making Responses API call with input type: {type(input).__name__}")

        # Make OpenAI Responses API call (stateless)
        response = await self._client.responses.create(
            model=self._model,
            input=responses_input,
            instructions=system.content if system and system.content else NOT_GIVEN,
            tools=tools,
        )

        self.logger.debug(f"Response API returned: {type(response)}")
        self.logger.debug(f"Response has content: {hasattr(response, 'content')}")
        if hasattr(response, "output"):
            self.logger.debug(f"Response content: {response.output}")
        self.logger.debug(f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}")

        # Convert response to ModelMessage format
        model_response = self._convert_from_responses_format(response)

        # If response has function calls, recursively execute them
        if model_response.function_calls:
            self.logger.debug(
                f"Response has {len(model_response.function_calls)} function calls, executing recursively"
            )
            return await self.generate_text(model_response, system=system, memory=memory, functions=functions)

        # Push response to memory (only if not recursing)
        await memory.push(model_response)

        # Handle streaming if callback provided
        if on_chunk and hasattr(response, "content"):
            if model_response.content:
                await on_chunk(model_response.content)

        self.logger.debug("Stateless Responses API conversation completed")
        return model_response

    async def _execute_functions(
        self, input: Message, functions: dict[str, Function[BaseModel]] | None
    ) -> list[FunctionMessage]:
        """Execute any pending function calls in the input message."""
        function_results: list[FunctionMessage] = []

        if isinstance(input, ModelMessage) and input.function_calls:
            # Execute any pending function calls
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
                            # No parameters case - just call the handler with no args
                            handler = cast(FunctionHandlerWithNoParams, function.handler)
                            result = handler()
                        if inspect.isawaitable(result):
                            fn_res = await result
                        else:
                            fn_res = result

                        # Create function result message
                        function_results.append(FunctionMessage(content=fn_res, function_id=call.id))
                    except Exception as e:
                        # Handle function execution errors
                        function_results.append(
                            FunctionMessage(content=f"Function execution failed: {str(e)}", function_id=call.id)
                        )

        return function_results

    def _convert_to_responses_format(
        self,
        input: Message | None,
        system: Message | None,
        messages: list[Message],
    ) -> str | ResponseInputParam:
        """Convert messages to Responses API input format."""
        input_list: ResponseInputParam = []

        # Extract all FunctionMessage from messages for lookup
        results_by_id = {msg.function_id: msg for msg in messages if isinstance(msg, FunctionMessage)}

        input_messages = list(messages)
        if input:
            input_messages.append(input)

        if system:
            input_messages.insert(0, system)

        for message in input_messages:
            if isinstance(message, UserMessage) or isinstance(message, SystemMessage):
                role = message.role
                content = message.content or ""
                input_list.append(EasyInputMessageParam(content=content, role=role, type="message"))
            elif isinstance(message, ModelMessage):
                if message.function_calls:
                    for call in message.function_calls:
                        # Add the function call
                        input_list.append(
                            ResponseFunctionToolCallParam(
                                type="function_call",
                                call_id=call.id,
                                name=call.name,
                                arguments=json.dumps(call.arguments),
                            )
                        )

                        # Add the matching function result
                        if call.id in results_by_id:
                            result = results_by_id[call.id]
                            input_list.append(
                                {
                                    "call_id": result.function_id,
                                    "output": result.content or "",
                                    "type": "function_call_output",
                                }
                            )
                        else:
                            self.logger.warning(f"No associated result found for call id ({call.name} - {call.id})")
                else:
                    # ModelMessage with content but no function calls
                    content = message.content or ""
                    input_list.append(EasyInputMessageParam(content=content, role="assistant", type="message"))
            elif isinstance(message, FunctionMessage):  # pyright: ignore [reportUnnecessaryIsInstance]
                # No-op: FunctionMessage is handled as part of ModelMessage function calls
                pass

        return input_list

    def _convert_functions_to_tools(self, functions: dict[str, Function[BaseModel]]) -> list[ToolParam]:
        """Convert functions to Responses API tools format."""
        tools: list[ToolParam] = []
        schema = {}

        for func in functions.values():
            # Get strict schema for Responses API using OpenAI's transformations
            if isinstance(func.parameter_schema, dict):
                # For raw JSON schemas, use OpenAI's strict transformation
                schema = get_function_schema(func)
                schema = _ensure_strict_json_schema(schema, path=(), root=schema)
            elif func.parameter_schema is not None:
                # Use OpenAI's official strict schema transformation for Pydantic models
                schema = to_strict_json_schema(func.parameter_schema)

            tools.append(
                FunctionToolParam(
                    strict=True,
                    type="function",
                    name=func.name,
                    description=func.description,
                    parameters=schema,
                )
            )

        return tools

    def _convert_from_responses_format(self, response: Response) -> ModelMessage:
        """Convert Responses API response to ModelMessage format."""
        content: str | None = None
        function_calls: list[FunctionCall] | None = None

        # Extract content from response - use the proper Response attributes
        content = response.output_text

        # Handle function calls from response
        if response.output:
            function_calls = []
            for response_output in response.output:
                if not isinstance(response_output, ResponseFunctionToolCall):
                    continue
                function_calls.append(
                    FunctionCall(
                        id=response_output.call_id,
                        name=response_output.name,
                        arguments=json.loads(response_output.arguments) if response_output.arguments else {},
                    )
                )

        return ModelMessage(content=content, function_calls=function_calls)
