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
    FunctionMessage,
    ListMemory,
    ModelMessage,
    SystemMessage,
    UserMessage,
)
from microsoft.teams.openai.responses_chat_model import OpenAIResponsesAIModel
from openai.types.responses import Response, ResponseFunctionToolCall
from pydantic import BaseModel


class FunctionTestParams(BaseModel):
    query: str


@pytest.fixture
def mock_openai_client() -> AsyncMock:
    client = AsyncMock()
    return client


@pytest.fixture
def stateful_model(mock_openai_client: AsyncMock) -> OpenAIResponsesAIModel:
    model_instance = OpenAIResponsesAIModel(key="fake-key", model="gpt-4", stateful=True)
    model_instance._client = mock_openai_client
    return model_instance


@pytest.fixture
def stateless_model(mock_openai_client: AsyncMock) -> OpenAIResponsesAIModel:
    model_instance = OpenAIResponsesAIModel(key="fake-key", model="gpt-4", stateful=False)
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


@pytest.fixture
def async_test_function() -> Function[FunctionTestParams]:
    async def handler(params: FunctionTestParams) -> str:
        return f"Async Result: {params.query}"

    return Function(
        name="async_test_function",
        description="An async test function",
        parameter_schema=FunctionTestParams,
        handler=handler,
    )


class TestOpenAIResponsesAIModel:
    @pytest.mark.asyncio
    async def test_generate_text_stateful_mode(self, stateful_model, mock_openai_client):
        # Setup mock response
        mock_response = MagicMock(spec=Response)
        mock_response.id = "response_123"
        mock_response.output_text = "Hello, world!"
        mock_response.output = []
        mock_openai_client.responses.create = AsyncMock(return_value=mock_response)

        # Test
        input_msg = UserMessage(content="Hello")
        result = await stateful_model.generate_text(input_msg)

        # Assertions
        assert result.content == "Hello, world!"
        assert result.id == "response_123"
        assert result.function_calls is None
        mock_openai_client.responses.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_text_stateless_mode(self, stateless_model, mock_openai_client):
        # Setup mock response
        mock_response = MagicMock(spec=Response)
        mock_response.output_text = "Stateless response"
        mock_response.output = []
        mock_openai_client.responses.create = AsyncMock(return_value=mock_response)

        # Test
        input_msg = UserMessage(content="Hello")
        result = await stateless_model.generate_text(input_msg)

        # Assertions
        assert result.content == "Stateless response"
        assert not hasattr(result, "id") or result.id is None
        mock_openai_client.responses.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_stateful_with_previous_response_id(self, stateful_model, mock_openai_client):
        # Setup mock responses
        mock_response1 = MagicMock(spec=Response)
        mock_response1.id = "response_123"
        mock_response1.output_text = "First response"
        mock_response1.output = []

        mock_response2 = MagicMock(spec=Response)
        mock_response2.id = "response_456"
        mock_response2.output_text = "Second response"
        mock_response2.output = []

        mock_openai_client.responses.create = AsyncMock(side_effect=[mock_response1, mock_response2])

        # First call
        input_msg1 = UserMessage(content="Hello")
        result1 = await stateful_model.generate_text(input_msg1)

        # Second call - pass memory with previous response already in it
        previous_response = ModelMessage(content="First response", function_calls=None)
        previous_response.id = "response_123"
        memory = ListMemory()
        await memory.set_all([previous_response])

        input_msg2 = UserMessage(content="How are you?")
        result2 = await stateful_model.generate_text(input_msg2, memory=memory)

        # Assertions
        assert result1.content == "First response"
        assert result2.content == "Second response"

        # Check that second call used previous_response_id
        second_call_args = mock_openai_client.responses.create.call_args_list[1]
        assert second_call_args[1]["previous_response_id"] == "response_123"

    @pytest.mark.asyncio
    async def test_function_execution_and_api_integration(self, stateful_model, mock_openai_client, test_function):
        # Setup mock responses for function call flow
        # First response: API returns function call
        mock_function_call = MagicMock(spec=ResponseFunctionToolCall)
        mock_function_call.call_id = "call_123"
        mock_function_call.name = "test_function"
        mock_function_call.arguments = '{"query": "hello world"}'

        mock_response1 = MagicMock(spec=Response)
        mock_response1.id = "response_123"
        mock_response1.output_text = None
        mock_response1.output = [mock_function_call]

        # Second response: API returns final answer after function execution
        mock_response2 = MagicMock(spec=Response)
        mock_response2.id = "response_456"
        mock_response2.output_text = "Based on the function result, here's my response"
        mock_response2.output = []

        mock_openai_client.responses.create = AsyncMock(side_effect=[mock_response1, mock_response2])

        # Test
        input_msg = UserMessage(content="Please call the test function with hello world")
        functions = {"test_function": test_function}
        result = await stateful_model.generate_text(input_msg, functions=functions)

        # Assertions
        assert result.content == "Based on the function result, here's my response"
        assert mock_openai_client.responses.create.call_count == 2

        # Validate first API call (with function definitions)
        first_call_args = mock_openai_client.responses.create.call_args_list[0]
        tools = first_call_args[1]["tools"]
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["name"] == "test_function"
        assert tools[0]["description"] == "A test function"
        assert tools[0]["strict"] is True
        assert tools[0]["parameters"]["additionalProperties"] is False

        # Validate second API call (includes function result)
        second_call_args = mock_openai_client.responses.create.call_args_list[1]
        second_input = second_call_args[1]["input"]

        # Should include function call and result
        function_call_found = False
        function_result_found = False
        for item in second_input:
            if item.get("type") == "function_call":
                assert item["call_id"] == "call_123"
                assert item["name"] == "test_function"
                function_call_found = True
            elif item.get("type") == "function_call_output":
                assert item["call_id"] == "call_123"
                assert item["output"] == "Result: hello world"  # This is what our test_function returns
                function_result_found = True

        assert function_call_found, "Function call not found in second API request"
        assert function_result_found, "Function result not found in second API request"

    @pytest.mark.asyncio
    async def test_stateless_with_memory(self, stateless_model, mock_openai_client):
        # Setup mock response
        mock_response = MagicMock(spec=Response)
        mock_response.output_text = "Memory response"
        mock_response.output = []
        mock_openai_client.responses.create = AsyncMock(return_value=mock_response)

        # Setup memory with previous messages
        memory = ListMemory()
        await memory.push(UserMessage(content="Previous message"))
        await memory.push(ModelMessage(content="Previous response", function_calls=None))

        # Test
        input_msg = UserMessage(content="Current message")
        result = await stateless_model.generate_text(input_msg, memory=memory)

        # Assertions
        assert result.content == "Memory response"
        call_args = mock_openai_client.responses.create.call_args
        input_param = call_args[1]["input"]

        # Should include all messages in input (previous messages + current message added twice due to stateless logic)
        assert len(input_param) == 4
        assert input_param[0]["content"] == "Previous message"
        assert input_param[1]["content"] == "Previous response"
        assert input_param[2]["content"] == "Current message"
        assert input_param[3]["content"] == "Current message"  # Added again in conversion

    @pytest.mark.asyncio
    async def test_responses_api_call_parameters(self, stateful_model, mock_openai_client, test_function):
        # Setup mock response
        mock_response = MagicMock(spec=Response)
        mock_response.id = "response_123"
        mock_response.output_text = "Test response"
        mock_response.output = []
        mock_openai_client.responses.create = AsyncMock(return_value=mock_response)

        # Test with all parameters
        input_msg = UserMessage(content="Test message")
        system_msg = SystemMessage(content="System instructions")
        memory = ListMemory()
        await memory.push(UserMessage(content="Previous message"))
        functions = {"test_function": test_function}

        await stateful_model.generate_text(input_msg, system=system_msg, memory=memory, functions=functions)

        # Validate API call parameters
        call_args = mock_openai_client.responses.create.call_args
        assert call_args[1]["model"] == "gpt-4"
        assert call_args[1]["instructions"] == "System instructions"
        assert call_args[1]["previous_response_id"] is None  # No previous response in memory

        input_param = call_args[1]["input"]
        assert len(input_param) == 2  # previous and current messages
        assert input_param[0]["content"] == "Previous message"
        assert input_param[1]["content"] == "Test message"

        tools = call_args[1]["tools"]
        assert len(tools) == 1
        assert tools[0]["type"] == "function"
        assert tools[0]["name"] == "test_function"
        assert tools[0]["description"] == "A test function"
        assert tools[0]["strict"] is True
        assert "additionalProperties" in tools[0]["parameters"]
        assert tools[0]["parameters"]["additionalProperties"] is False

    @pytest.mark.asyncio
    async def test_execute_functions_success(self, stateful_model, test_function):
        # Test successful function execution
        function_call = FunctionCall(id="call_1", name="test_function", arguments={"query": "hello"})
        model_msg = ModelMessage(content=None, function_calls=[function_call])
        functions = {"test_function": test_function}

        results = await stateful_model._execute_functions(model_msg, functions)

        assert len(results) == 1
        assert results[0].content == "Result: hello"
        assert results[0].function_id == "call_1"

    @pytest.mark.asyncio
    async def test_execute_functions_error_handling(self, stateful_model):
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

        results = await stateful_model._execute_functions(model_msg, functions)

        assert len(results) == 1
        assert "Function execution failed: Test error" in results[0].content
        assert results[0].function_id == "call_1"

    @pytest.mark.asyncio
    async def test_recursive_function_calls(self, stateful_model, mock_openai_client, test_function):
        # Setup mock responses for recursive calls
        # First response with function call
        mock_response1 = MagicMock(spec=Response)
        mock_response1.id = "response_123"
        mock_response1.output_text = None
        mock_function_call = MagicMock(spec=ResponseFunctionToolCall)
        mock_function_call.call_id = "call_1"
        mock_function_call.name = "test_function"
        mock_function_call.arguments = '{"query": "test"}'
        mock_response1.output = [mock_function_call]

        # Second response with final answer
        mock_response2 = MagicMock(spec=Response)
        mock_response2.id = "response_456"
        mock_response2.output_text = "Final response"
        mock_response2.output = []

        mock_openai_client.responses.create = AsyncMock(side_effect=[mock_response1, mock_response2])

        # Test
        input_msg = UserMessage(content="Use the function")
        functions = {"test_function": test_function}
        result = await stateful_model.generate_text(input_msg, functions=functions)

        # Assertions
        assert result.content == "Final response"
        assert mock_openai_client.responses.create.call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_execution(self, stateful_model, async_test_function):
        # Test async function execution
        function_call = FunctionCall(id="call_1", name="async_test_function", arguments={"query": "hello"})
        model_msg = ModelMessage(content=None, function_calls=[function_call])
        functions = {"async_test_function": async_test_function}

        results = await stateful_model._execute_functions(model_msg, functions)

        assert len(results) == 1
        assert results[0].content == "Async Result: hello"
        assert results[0].function_id == "call_1"

    @pytest.mark.asyncio
    async def test_convert_to_responses_format_with_function_calls(self, stateful_model):
        # Test message conversion with function calls and results
        function_call = FunctionCall(id="call_1", name="test_function", arguments={"query": "test"})
        model_msg = ModelMessage(content=None, function_calls=[function_call])
        function_result = FunctionMessage(content="Function result", function_id="call_1")

        messages = [model_msg, function_result]
        input_msg = UserMessage(content="Follow up")

        result = stateful_model._convert_to_responses_format(input_msg, None, messages)

        # Should have function call, function result, and user message
        assert len(result) == 3
        assert result[0]["type"] == "function_call"
        assert result[0]["call_id"] == "call_1"
        assert result[0]["name"] == "test_function"
        assert result[1]["type"] == "function_call_output"
        assert result[1]["call_id"] == "call_1"
        assert result[1]["output"] == "Function result"
        assert result[2]["type"] == "message"
        assert result[2]["content"] == "Follow up"
