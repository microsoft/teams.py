"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable
from unittest.mock import Mock

import pytest
from microsoft.teams.ai import (
    ChatPrompt,
    ChatSendResult,
    Function,
    FunctionCall,
    ListMemory,
    Memory,
    ModelMessage,
    SystemMessage,
    UserMessage,
)
from pydantic import BaseModel


class MockFunctionParams(BaseModel):
    value: str


class MockAIModel:
    def __init__(self, should_call_function: bool = False, streaming_chunks: list[str] | None = None):
        self.should_call_function = should_call_function
        self.streaming_chunks = streaming_chunks or []

    async def generate_text(
        self,
        input: Any,
        *,
        system: SystemMessage | None = None,
        memory: Memory | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
    ) -> ModelMessage:
        # Simulate memory updates (like real AI model implementations)
        if memory is not None:
            await memory.push(input)  # Add input to memory

        # Generate response content
        content = f"GENERATED - {input.content}"

        # Handle streaming
        if on_chunk and self.streaming_chunks:
            for chunk in self.streaming_chunks:
                await on_chunk(chunk)

        # Handle function calling and execution
        function_calls = None
        if self.should_call_function and functions and "test_function" in functions:
            function_calls = [FunctionCall(id="call_123", name="test_function", arguments={"value": "test_input"})]

            # Actually execute the function (simulate real behavior)
            function = functions["test_function"]
            try:
                params = function.parameter_schema(value="test_input")
                result = function.handler(params)
                # In real implementation, function result would be added to memory
                # and conversation would continue recursively
                content += f" | Function result: {result}"
            except Exception as e:
                content += f" | Function error: {str(e)}"

        response = ModelMessage(content=content, function_calls=function_calls)

        # Add response to memory (like real AI model implementations)
        if memory is not None:
            await memory.push(response)

        return response


@pytest.fixture
def mock_model() -> MockAIModel:
    return MockAIModel()


@pytest.fixture
def mock_function_handler() -> Mock:
    handler = Mock(return_value="Function executed successfully")
    return handler


@pytest.fixture
def test_function(mock_function_handler: Mock) -> Function[MockFunctionParams]:
    return Function(
        name="test_function",
        description="A test function",
        parameter_schema=MockFunctionParams,
        handler=mock_function_handler,
    )


class TestChatPromptEssentials:
    def test_initialization(self, mock_model: MockAIModel) -> None:
        """Test basic initialization and function registration"""
        prompt = ChatPrompt(mock_model)
        assert prompt.model is mock_model
        assert prompt.functions == {}

        # Test function chaining
        def handler(params: MockFunctionParams) -> str:
            return "test"

        func = Function("test", "test", MockFunctionParams, handler)
        result = prompt.with_function(func)

        assert result is prompt  # Should return self for chaining
        assert "test" in prompt.functions

    @pytest.mark.asyncio
    async def test_string_input_conversion(self, mock_model: MockAIModel) -> None:
        """Test that string input is converted to UserMessage"""
        prompt = ChatPrompt(mock_model)
        result = await prompt.send("Hello world")

        assert isinstance(result, ChatSendResult)
        assert result.response.content == "GENERATED - Hello world"

    @pytest.mark.asyncio
    async def test_memory_updates(self) -> None:
        """Test that memory is actually updated with input and response"""
        memory = ListMemory()
        mock_model = MockAIModel()
        prompt = ChatPrompt(mock_model)

        # Send first message
        await prompt.send("First message", memory=memory)
        messages = await memory.get_all()
        assert len(messages) == 2  # Input + response should be added by model
        assert isinstance(messages[0], UserMessage)
        assert messages[0].content == "First message"
        assert isinstance(messages[1], ModelMessage)
        assert messages[1].content == "GENERATED - First message"

        # Send second message
        await prompt.send("Second message", memory=memory)
        messages = await memory.get_all()
        assert len(messages) == 4  # 2 previous + 2 new messages
        assert messages[2].content == "Second message"
        assert messages[3].content == "GENERATED - Second message"

    @pytest.mark.asyncio
    async def test_function_handler_execution(self, mock_function_handler: Mock) -> None:
        """Test that function handlers are actually called when model returns function calls"""
        # Create a mock model that will call functions
        mock_model = MockAIModel(should_call_function=True)

        # Create function with mock handler
        test_function = Function(
            name="test_function",
            description="A test function",
            parameter_schema=MockFunctionParams,
            handler=mock_function_handler,
        )

        prompt = ChatPrompt(mock_model, functions=[test_function])
        result = await prompt.send("Call the function")

        # Verify the function call is in the response
        assert result.response.function_calls is not None
        assert len(result.response.function_calls) == 1
        assert result.response.function_calls[0].name == "test_function"

        # Verify the function handler was actually called
        mock_function_handler.assert_called_once()
        called_params = mock_function_handler.call_args[0][0]
        assert isinstance(called_params, MockFunctionParams)
        assert called_params.value == "test_input"

        # Verify function result is included in response
        assert result.response.content is not None
        assert "Function result: Function executed successfully" in result.response.content

    @pytest.mark.asyncio
    async def test_streaming_callback(self) -> None:
        """Test that streaming callback receives chunks"""
        chunks_received: list[str] = []

        async def on_chunk(chunk: str) -> None:
            chunks_received.append(chunk)

        # Create model with streaming chunks
        mock_model = MockAIModel(streaming_chunks=["Hello", " ", "world"])
        prompt = ChatPrompt(mock_model)

        result = await prompt.send("Test streaming", on_chunk=on_chunk)

        # Verify chunks were received
        assert chunks_received == ["Hello", " ", "world"]
        assert isinstance(result, ChatSendResult)

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self, test_function: Function[MockFunctionParams]) -> None:
        """Test complete conversation with memory persistence"""
        memory = ListMemory()
        mock_model = MockAIModel()
        prompt = ChatPrompt(mock_model, functions=[test_function])

        # First exchange
        result1 = await prompt.send("Hello", memory=memory)
        assert result1.response.content == "GENERATED - Hello"

        # Second exchange
        result2 = await prompt.send("How are you?", memory=memory)
        assert result2.response.content == "GENERATED - How are you?"

        # Verify memory contains complete conversation history
        messages = await memory.get_all()
        assert len(messages) == 4  # 2 exchanges = 4 messages total
        assert messages[0].content == "Hello"
        assert messages[1].content == "GENERATED - Hello"
        assert messages[2].content == "How are you?"
        assert messages[3].content == "GENERATED - How are you?"

    @pytest.mark.asyncio
    async def test_error_handling(self) -> None:
        """Test basic error propagation"""

        class FailingMockModel:
            async def generate_text(self, *args: Any, **kwargs: Any) -> ModelMessage:
                raise ValueError("Model failed")

        prompt = ChatPrompt(FailingMockModel())

        with pytest.raises(ValueError, match="Model failed"):
            await prompt.send("Test")

    @pytest.mark.asyncio
    async def test_function_registration_workflow(self, mock_model: MockAIModel) -> None:
        """Test dynamic function registration and usage"""
        prompt = ChatPrompt(mock_model)
        assert len(prompt.functions) == 0

        # Add function dynamically
        def handler(params: MockFunctionParams) -> str:
            return f"Dynamic: {params.value}"

        func1 = Function("func1", "First function", MockFunctionParams, handler)
        func2 = Function("func2", "Second function", MockFunctionParams, handler)

        # Test chaining
        prompt.with_function(func1).with_function(func2)

        assert len(prompt.functions) == 2
        assert "func1" in prompt.functions
        assert "func2" in prompt.functions

        # Test overwriting
        func1_new = Function("func1", "Overwritten function", MockFunctionParams, handler)
        prompt.with_function(func1_new)

        assert len(prompt.functions) == 2  # Still 2 functions
        assert prompt.functions["func1"] is func1_new  # But func1 is replaced

    @pytest.mark.asyncio
    async def test_different_message_types(self, mock_model: MockAIModel) -> None:
        """Test handling different input message types"""
        prompt = ChatPrompt(mock_model)

        # String input
        result1 = await prompt.send("String input")
        assert result1.response.content == "GENERATED - String input"

        # UserMessage input
        user_msg = UserMessage(content="User message")
        result2 = await prompt.send(user_msg)
        assert result2.response.content == "GENERATED - User message"

        # ModelMessage input (for function calling scenarios)
        model_msg = ModelMessage(content="Model message", function_calls=None)
        result3 = await prompt.send(model_msg)
        assert result3.response.content == "GENERATED - Model message"
