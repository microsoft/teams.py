"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
import json
from typing import Union

from microsoft.teams.ai import (
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
from openai import NOT_GIVEN, AsyncAzureOpenAI, AsyncOpenAI
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionAssistantMessageParam,
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionMessageFunctionToolCallParam,
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionToolMessageParam,
    ChatCompletionToolUnionParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel


class OpenAIChatModel:
    def __init__(
        self,
        client_or_key: Union[AsyncOpenAI, str],
        model: str,
        *,
        base_url: str | None = None,
        # Azure OpenAI options
        azure_endpoint: str | None = None,
        api_version: str | None = None,
    ):
        if isinstance(client_or_key, (AsyncOpenAI, AsyncAzureOpenAI)):
            self._client = client_or_key
        else:
            # client_or_key is the API key
            if azure_endpoint:
                self._client = AsyncAzureOpenAI(
                    api_key=client_or_key, azure_endpoint=azure_endpoint, api_version=api_version
                )
            else:
                self._client = AsyncOpenAI(api_key=client_or_key, base_url=base_url)
        self.model = model

    async def send(
        self,
        input: Message,
        *,
        system: Message | None = None,
        memory: Memory | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
    ) -> ModelMessage:
        # Use default memory if none provided
        if memory is None:
            memory = ListMemory()

        # Execute any pending function calls first
        function_results = await self._execute_functions(input, functions)

        # Get conversation history from memory (make a copy to avoid modifying memory's internal state)
        messages = list(await memory.get_all())
        print(messages, function_results)

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
        print(openai_messages)

        # Convert functions to OpenAI tools format if provided
        tools = self._convert_functions(functions) if functions else NOT_GIVEN

        # Make OpenAI API call
        response = await self._client.chat.completions.create(model=self.model, messages=openai_messages, tools=tools)

        # Convert response back to ModelMessage format
        model_response = self._convert_response(response)

        # If response has function calls, recursively execute them
        if model_response.function_calls:
            return await self.send(model_response, system=system, memory=memory, functions=functions)

        # Push response to memory (only if not recursing)
        await memory.push(model_response)

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
                        # Parse arguments into Pydantic model
                        parsed_args = function.parameter_schema(**call.arguments)

                        # Handle both sync and async function handlers
                        result = function.handler(parsed_args)
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

    def _convert_messages(
        self, input: Message | None, system: Message | None, messages: list[Message] | None
    ) -> list[ChatCompletionMessageParam]:
        openai_messages: list[ChatCompletionMessageParam] = []

        # Add system message if provided
        if system and system.content:
            openai_messages.append(ChatCompletionSystemMessageParam(content=system.content, role="system"))

        # Add conversation history if provided
        if messages:
            for msg in messages:
                openai_messages.append(self._message_to_openai(msg))

        # Add the input message (if provided)
        if input:
            openai_messages.append(self._message_to_openai(input))

        return openai_messages

    def _message_to_openai(self, message: Message) -> ChatCompletionMessageParam:
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
        else:  # ModelMessage
            if message.function_calls:
                tool_calls = [
                    ChatCompletionMessageFunctionToolCallParam(
                        id=call.id, function={"name": call.name, "arguments": str(call.arguments)}, type="function"
                    )
                    for call in message.function_calls
                ]
            else:
                tool_calls = []

            return ChatCompletionAssistantMessageParam(role="assistant", content=message.content, tool_calls=tool_calls)

    def _convert_functions(self, functions: dict[str, Function[BaseModel]]) -> list[ChatCompletionToolUnionParam]:
        return [
            {
                "type": "function",
                "function": {
                    "name": func.name,
                    "description": func.description,
                    "parameters": func.parameter_schema.model_json_schema(),
                },
            }
            for func in functions.values()
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
