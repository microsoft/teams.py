"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.ai import (
    Function,
    FunctionCall,
    ListMemory,
    ModelMessage,
    SystemMessage,
    UserMessage,
)
from microsoft.teams.openai.completions_model import OpenAICompletionsAIModel
from openai import NOT_GIVEN
from openai._streaming import AsyncStream
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionMessageFunctionToolCall,
)
from pydantic import BaseModel


class FunctionTestParams(BaseModel):
    query: str


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    client = AsyncMock()
    return client


@pytest.fixture
def model(mock_openai_client: AsyncMock) -> OpenAICompletionsAIModel:
    model_instance = OpenAICompletionsAIModel(key="fake-key", model="gpt-4")
    model_instance._client = mock_openai_client
    return model_instance


@pytest.fixture
def test_function() -> Function[FunctionTestParams]:
    def handler(params: FunctionTestParams) -> str:
        return f"Result: {params.query}"

    return Function(
        name="test_function",
        description="A test function",
        parameter_schema=FunctionTestParams,
        handler=handler,
    )


class TestOpenAICompletionsAIModel:
    @pytest.mark.asyncio
    async def test_generate_text_basic_message(
        self, model: OpenAICompletionsAIModel, mock_openai_client: AsyncMock
    ) -> None:
        # Setup mock response
        mock_message = ChatCompletionMessage(role="assistant", content="Hello, world!")
        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test
        input_msg = UserMessage(content="Hello")
        result = await model.generate_text(input_msg)

        # Assertions
        assert result.content == "Hello, world!"
        assert result.function_calls is None

        # Validate API call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["stream"] is False

        messages = call_args[1]["messages"]
        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Hello"

        # Should not have tools when no functions provided
        assert "tools" not in call_args[1] or call_args[1]["tools"] is NOT_GIVEN

        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_text_with_system_message(self, model, mock_openai_client):
        # Setup mock response
        mock_message = ChatCompletionMessage(role="assistant", content="System response")
        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test
        input_msg = UserMessage(content="Hello")
        system_msg = SystemMessage(content="You are a helpful assistant")
        result = await model.generate_text(input_msg, system=system_msg)

        # Assertions
        assert result.content == "System response"
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are a helpful assistant"

    @pytest.mark.asyncio
    async def test_generate_text_with_memory(self, model, mock_openai_client):
        # Setup mock response
        mock_message = ChatCompletionMessage(role="assistant", content="Memory response")
        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Setup memory with conversation history
        memory = ListMemory()
        conversation_history = [
            ("user", "First user message"),
            ("assistant", "First assistant response"),
            ("user", "Second user message"),
            ("assistant", "Second assistant response"),
            ("user", "Third user message"),
        ]

        for role, content in conversation_history:
            if role == "user":
                await memory.push(UserMessage(content=content))
            else:
                await memory.push(ModelMessage(content=content, function_calls=None))

        # Test
        input_msg = UserMessage(content="Current message")
        result = await model.generate_text(input_msg, memory=memory)

        # Assertions
        assert result.content == "Memory response"
        call_args = mock_openai_client.chat.completions.create.call_args
        messages = call_args[1]["messages"]

        # Verify expected messages were sent to API
        expected_messages = conversation_history + [("user", "Current message")]
        assert len(messages) == len(expected_messages)

        for i, (expected_role, expected_content) in enumerate(expected_messages):
            assert messages[i]["role"] == expected_role
            assert messages[i]["content"] == expected_content

        # Verify API call parameters
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["stream"] is False

    @pytest.mark.asyncio
    async def test_generate_text_with_functions(self, model, mock_openai_client, test_function):
        # Setup mock response
        mock_message = ChatCompletionMessage(role="assistant", content="Function response")
        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test
        input_msg = UserMessage(content="Use the function")
        functions = {"test_function": test_function}
        result = await model.generate_text(input_msg, functions=functions)

        # Assertions
        assert result.content == "Function response"
        call_args = mock_openai_client.chat.completions.create.call_args
        tools = call_args[1]["tools"]
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "test_function"

    @pytest.mark.asyncio
    async def test_generate_text_with_streaming(self, model, mock_openai_client):
        # Setup mock streaming response
        mock_delta1 = MagicMock()
        mock_delta1.content = "Hello"
        mock_delta1.tool_calls = None
        mock_choice1 = MagicMock()
        mock_choice1.delta = mock_delta1
        mock_chunk1 = MagicMock(spec=ChatCompletionChunk)
        mock_chunk1.choices = [mock_choice1]

        mock_delta2 = MagicMock()
        mock_delta2.content = " world"
        mock_delta2.tool_calls = None
        mock_choice2 = MagicMock()
        mock_choice2.delta = mock_delta2
        mock_chunk2 = MagicMock(spec=ChatCompletionChunk)
        mock_chunk2.choices = [mock_choice2]

        mock_stream = AsyncMock(spec=AsyncStream)
        mock_stream.__aiter__.return_value = [mock_chunk1, mock_chunk2]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream)

        # Test
        chunks = []

        async def on_chunk(chunk):
            chunks.append(chunk)

        input_msg = UserMessage(content="Hello")
        result = await model.generate_text(input_msg, on_chunk=on_chunk)

        # Assertions
        assert result.content == "Hello world"
        assert chunks == ["Hello", " world"]
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["stream"] is True

    @pytest.mark.asyncio
    async def test_generate_text_with_function_calls_recursive(self, model, mock_openai_client, test_function):
        # Setup mock responses for recursive calls
        # First response with function call
        mock_function = MagicMock()
        mock_function.name = "test_function"
        mock_function.arguments = '{"query": "test"}'

        mock_tool_call = MagicMock(spec=ChatCompletionMessageFunctionToolCall)
        mock_tool_call.id = "call_1"
        mock_tool_call.type = "function"
        mock_tool_call.function = mock_function

        mock_message1 = ChatCompletionMessage(
            role="assistant",
            content=None,
            tool_calls=[mock_tool_call],
        )
        mock_choice1 = MagicMock()
        mock_choice1.message = mock_message1

        mock_response1 = MagicMock(spec=ChatCompletion)
        mock_response1.choices = [mock_choice1]

        # Second response with final answer
        mock_message2 = ChatCompletionMessage(role="assistant", content="Final response")
        mock_choice2 = MagicMock()
        mock_choice2.message = mock_message2

        mock_response2 = MagicMock(spec=ChatCompletion)
        mock_response2.choices = [mock_choice2]

        mock_openai_client.chat.completions.create = AsyncMock(side_effect=[mock_response1, mock_response2])

        # Test
        input_msg = UserMessage(content="Use the function")
        functions = {"test_function": test_function}
        result = await model.generate_text(input_msg, functions=functions)

        # Assertions
        assert result.content == "Final response"
        assert mock_openai_client.chat.completions.create.call_count == 2

    @pytest.mark.asyncio
    async def test_openai_api_call_parameters(self, model, mock_openai_client, test_function):
        # Setup mock response
        mock_message = ChatCompletionMessage(role="assistant", content="Test response")
        mock_choice = MagicMock()
        mock_choice.message = mock_message

        mock_response = MagicMock(spec=ChatCompletion)
        mock_response.choices = [mock_choice]
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        # Test with all parameters
        input_msg = UserMessage(content="Test message")
        system_msg = SystemMessage(content="System prompt")
        memory = ListMemory()
        await memory.push(UserMessage(content="Previous message"))
        functions = {"test_function": test_function}

        await model.generate_text(input_msg, system=system_msg, memory=memory, functions=functions)

        # Validate API call parameters
        call_args = mock_openai_client.chat.completions.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["stream"] is False

        messages = call_args[1]["messages"]
        assert len(messages) == 3  # system, previous, current
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "System prompt"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Previous message"
        assert messages[2]["role"] == "user"
        assert messages[2]["content"] == "Test message"

        tools = call_args[1]["tools"]
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["function"]["name"] == "test_function"
        assert tools[0]["function"]["description"] == "A test function"

    @pytest.mark.asyncio
    async def test_execute_functions_success(self, model, test_function):
        # Test successful function execution
        function_call = FunctionCall(id="call_1", name="test_function", arguments={"query": "hello"})
        model_msg = ModelMessage(content=None, function_calls=[function_call])
        functions = {"test_function": test_function}

        results = await model._execute_functions(model_msg, functions)

        assert len(results) == 1
        assert results[0].content == "Result: hello"
        assert results[0].function_id == "call_1"

    @pytest.mark.asyncio
    async def test_execute_functions_error_handling(self, model):
        # Test function execution error handling
        def error_handler(params: FunctionTestParams):
            raise ValueError("Test error")

        error_function = Function(
            name="error_function",
            description="A function that errors",
            parameter_schema=FunctionTestParams,
            handler=error_handler,
        )

        function_call = FunctionCall(id="call_1", name="error_function", arguments={"query": "test"})
        model_msg = ModelMessage(content=None, function_calls=[function_call])
        functions = {"error_function": error_function}

        results = await model._execute_functions(model_msg, functions)

        assert len(results) == 1
        assert "Function execution failed: Test error" in results[0].content
        assert results[0].function_id == "call_1"

    @pytest.mark.asyncio
    async def test_streaming_response_handling(self, model):
        # Setup mock streaming response with function calls
        mock_delta1 = MagicMock()
        mock_delta1.content = "Hello"
        mock_delta1.tool_calls = None
        mock_choice1 = MagicMock()
        mock_choice1.delta = mock_delta1
        mock_chunk1 = MagicMock(spec=ChatCompletionChunk)
        mock_chunk1.choices = [mock_choice1]

        tool_call_delta = MagicMock()
        tool_call_delta.index = 0
        tool_call_delta.id = "call_"
        tool_call_delta.function = MagicMock()
        tool_call_delta.function.name = "test"
        tool_call_delta.function.arguments = '{"key":'

        mock_delta2 = MagicMock()
        mock_delta2.content = None
        mock_delta2.tool_calls = [tool_call_delta]
        mock_choice2 = MagicMock()
        mock_choice2.delta = mock_delta2
        mock_chunk2 = MagicMock(spec=ChatCompletionChunk)
        mock_chunk2.choices = [mock_choice2]

        tool_call_delta2 = MagicMock()
        tool_call_delta2.index = 0
        tool_call_delta2.id = "1"
        tool_call_delta2.function = MagicMock()
        tool_call_delta2.function.name = "_func"
        tool_call_delta2.function.arguments = '"value"}'

        mock_delta3 = MagicMock()
        mock_delta3.content = None
        mock_delta3.tool_calls = [tool_call_delta2]
        mock_choice3 = MagicMock()
        mock_choice3.delta = mock_delta3
        mock_chunk3 = MagicMock(spec=ChatCompletionChunk)
        mock_chunk3.choices = [mock_choice3]

        mock_stream = AsyncMock(spec=AsyncStream)
        mock_stream.__aiter__.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]

        chunks = []

        async def on_chunk(chunk):
            chunks.append(chunk)

        result = await model._handle_streaming_response(mock_stream, on_chunk)

        assert result.content == "Hello"
        assert len(result.function_calls) == 1
        assert result.function_calls[0].id == "call_1"
        assert result.function_calls[0].name == "test_func"
        assert result.function_calls[0].arguments == {"key": "value"}
        assert chunks == ["Hello"]
