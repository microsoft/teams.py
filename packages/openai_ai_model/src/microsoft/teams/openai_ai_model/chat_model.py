"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
from typing import Union

from microsoft.teams.ai import (
    Function,
    FunctionCall,
    FunctionMessage,
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
        messages: list[Message] | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
    ) -> ModelMessage:
        # Convert messages to OpenAI format
        openai_messages = self._convert_messages(input, system, messages)

        # Convert functions to OpenAI tools format if provided
        tools = self._convert_functions(functions) if functions else NOT_GIVEN

        # Make OpenAI API call
        response = await self._client.chat.completions.create(model=self.model, messages=openai_messages, tools=tools)

        # Convert response back to ModelMessage format
        return self._convert_response(response)

    def _convert_messages(
        self, input: Message, system: Message | None, messages: list[Message] | None
    ) -> list[ChatCompletionMessageParam]:
        openai_messages: list[ChatCompletionMessageParam] = []

        # Add system message if provided
        if system and system.content:
            openai_messages.append(ChatCompletionSystemMessageParam(content=system.content, role="system"))

        # Add conversation history if provided
        if messages:
            for msg in messages:
                openai_messages.append(self._message_to_openai(msg))

        # Add the input message
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
