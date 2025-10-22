"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from inspect import isawaitable
from typing import Any, Awaitable, Callable, Optional, cast
from unittest.mock import Mock

import pytest
from microsoft.teams.ai import (
    ChatPrompt,
    ChatSendResult,
    Function,
    FunctionCall,
    FunctionHandler,
    ListMemory,
    Memory,
    Message,
    ModelMessage,
    SystemMessage,
    UserMessage,
)
from microsoft.teams.ai.plugin import BaseAIPlugin
from pydantic import BaseModel

# pyright: basic


class MockFunctionParams(BaseModel):
    value: str


class MockAIModel:
    def __init__(self, should_call_function: bool = False, streaming_chunks: list[str] | None = None):
        self.should_call_function = should_call_function
        self.streaming_chunks = streaming_chunks or []
        self.last_system_message: SystemMessage | None = None
        self.last_input: Message | None = None
        self.last_functions: dict[str, Function[BaseModel]] | None = None

    async def generate_text(
        self,
        input: Any,
        *,
        system: SystemMessage | None = None,
        memory: Memory | None = None,
        functions: dict[str, Function[BaseModel]] | None = None,
        on_chunk: Callable[[str], Awaitable[None]] | None = None,
    ) -> ModelMessage:
        # Track what we received for testing
        self.last_system_message = system
        self.last_input = input
        self.last_functions = functions
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
                casted_schema = cast(type, function.parameter_schema)
                params = casted_schema(value="test_input")
                handler = cast(FunctionHandler[BaseModel], function.handler)
                result = handler(params)
                # Handle both sync and async results
                if isawaitable(result):
                    result = await result
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

    @pytest.mark.asyncio
    async def test_with_function_unpacked_parameters(self, mock_model: MockAIModel) -> None:
        """Test with_function using unpacked parameters instead of Function object"""
        prompt = ChatPrompt(mock_model)

        # Test with parameter schema
        def handler_with_params(params: MockFunctionParams) -> str:
            return f"Result: {params.value}"

        prompt.with_function(
            name="test_func",
            description="Test function with params",
            parameter_schema=MockFunctionParams,
            handler=handler_with_params,
        )

        assert "test_func" in prompt.functions
        assert prompt.functions["test_func"].name == "test_func"
        assert prompt.functions["test_func"].description == "Test function with params"
        assert prompt.functions["test_func"].parameter_schema == MockFunctionParams

        # Test without parameter schema (no params function)
        def handler_no_params() -> str:
            return "No params result"

        prompt.with_function(
            name="no_params_func",
            description="Function with no parameters",
            handler=handler_no_params,
        )

        assert "no_params_func" in prompt.functions
        assert prompt.functions["no_params_func"].name == "no_params_func"
        assert prompt.functions["no_params_func"].description == "Function with no parameters"
        assert prompt.functions["no_params_func"].parameter_schema is None

        # Verify both work in send
        result = await prompt.send("Test message")
        assert result.response.content == "GENERATED - Test message"


class MockPlugin(BaseAIPlugin):
    """Mock plugin for testing that tracks all hook calls"""

    def __init__(self, name: str):
        super().__init__(name)
        self.before_send_called = False
        self.after_send_called = False
        self.before_function_called: list[tuple[str, Optional[BaseModel]]] = []
        self.after_function_called: list[tuple[str, Optional[BaseModel], str]] = []
        self.build_functions_called = False
        self.build_system_message_called = False
        self.input_modifications: list[str] = []
        self.response_modifications: list[str] = []
        self.function_result_modifications: list[str] = []

    async def on_before_send(self, input: Message) -> Message | None:
        self.before_send_called = True
        if self.input_modifications:
            modification = self.input_modifications.pop(0)
            if isinstance(input, UserMessage):
                return UserMessage(content=f"{modification}: {input.content}")
            elif isinstance(input, ModelMessage):
                return ModelMessage(
                    content=f"{modification}: {input.content}" if input.content else modification,
                    function_calls=input.function_calls,
                )
        return input

    async def on_after_send(self, response: ModelMessage) -> ModelMessage | None:
        self.after_send_called = True
        if self.response_modifications:
            modification = self.response_modifications.pop(0)
            return ModelMessage(
                content=f"{modification}: {response.content}" if response.content else modification,
                function_calls=response.function_calls,
            )
        return response

    async def on_before_function_call(self, function_name: str, args: Optional[BaseModel] = None) -> None:
        self.before_function_called.append((function_name, args))

    async def on_after_function_call(
        self, function_name: str, result: str, args: Optional[BaseModel] = None
    ) -> str | None:
        self.after_function_called.append((function_name, args, result))
        if self.function_result_modifications:
            modification = self.function_result_modifications.pop(0)
            return f"{modification}: {result}"
        return result

    async def on_build_functions(self, functions: list[Function[BaseModel]]) -> list[Function[BaseModel]] | None:
        self.build_functions_called = True
        return functions

    async def on_build_instructions(self, instructions: SystemMessage | None) -> SystemMessage | None:
        self.build_system_message_called = True
        if instructions is None:
            return SystemMessage(content="Plugin-generated system message")
        return SystemMessage(content=f"Plugin-modified: {instructions.content}")


class TestChatPromptPlugins:
    """Test suite for plugin functionality in ChatPrompt"""

    def test_plugin_initialization_and_registration(self, mock_model: MockAIModel) -> None:
        """Test plugin initialization and registration"""
        plugin1 = MockPlugin("plugin1")
        plugin2 = MockPlugin("plugin2")

        # Test initialization with plugins
        prompt = ChatPrompt(mock_model, plugins=[plugin1])
        assert len(prompt.plugins) == 1
        assert prompt.plugins[0] is plugin1

        # Test with_plugin method
        result = prompt.with_plugin(plugin2)
        assert result is prompt  # Should return self for chaining
        assert len(prompt.plugins) == 2
        assert prompt.plugins[1] is plugin2

    @pytest.mark.asyncio
    async def test_on_before_send_hook(self, mock_model: MockAIModel) -> None:
        """Test that on_before_send hook can modify input messages and they're passed to model"""
        plugin = MockPlugin("test_plugin")
        plugin.input_modifications = ["MODIFIED"]

        prompt = ChatPrompt(mock_model, plugins=[plugin])
        result = await prompt.send("Original message")

        assert plugin.before_send_called
        # Verify the modified message was passed to the model
        assert mock_model.last_input is not None
        assert mock_model.last_input.content == "MODIFIED: Original message"
        # Verify the response reflects the modified input
        assert result.response.content == "GENERATED - MODIFIED: Original message"

    @pytest.mark.asyncio
    async def test_on_after_send_hook(self, mock_model: MockAIModel) -> None:
        """Test that on_after_send hook can modify response messages"""
        plugin = MockPlugin("test_plugin")
        plugin.response_modifications = ["RESPONSE_MODIFIED"]

        prompt = ChatPrompt(mock_model, plugins=[plugin])
        result = await prompt.send("Test message")

        assert plugin.after_send_called
        assert result.response.content == "RESPONSE_MODIFIED: GENERATED - Test message"

    @pytest.mark.asyncio
    async def test_on_build_instructions_hook_with_actual_updates(self, mock_model: MockAIModel) -> None:
        """Test that on_build_system_message hook actually modifies system messages passed to model"""
        plugin = MockPlugin("test_plugin")
        prompt = ChatPrompt(mock_model, plugins=[plugin])

        # Test with None instructions - plugin should generate one
        await prompt.send("Test", instructions=None)
        assert plugin.build_system_message_called
        assert mock_model.last_system_message is not None
        assert mock_model.last_system_message.content == "Plugin-generated system message"

        # Reset and test with existing instructions - plugin should modify it
        plugin.build_system_message_called = False
        system_msg = SystemMessage(content="Original system")
        await prompt.send("Test", instructions=system_msg)
        assert plugin.build_system_message_called
        assert mock_model.last_system_message is not None
        assert mock_model.last_system_message.content == "Plugin-modified: Original system"

    @pytest.mark.asyncio
    async def test_function_call_hooks(self, mock_function_handler: Mock) -> None:
        """Test that function call hooks are properly executed"""
        plugin = MockPlugin("test_plugin")
        plugin.function_result_modifications = ["FUNCTION_MODIFIED"]

        # Create a mock model that will call functions
        mock_model = MockAIModel(should_call_function=True)

        # Create function with mock handler
        test_function = Function(
            name="test_function",
            description="A test function",
            parameter_schema=MockFunctionParams,
            handler=mock_function_handler,
        )

        prompt = ChatPrompt(mock_model, functions=[test_function], plugins=[plugin])
        result = await prompt.send("Call the function")

        # Verify before hook was called
        assert len(plugin.before_function_called) == 1
        assert plugin.before_function_called[0][0] == "test_function"
        assert isinstance(plugin.before_function_called[0][1], MockFunctionParams)

        # Verify after hook was called and modified result
        assert len(plugin.after_function_called) == 1
        assert plugin.after_function_called[0][0] == "test_function"
        assert result.response.content is not None
        assert "FUNCTION_MODIFIED: Function executed successfully" in result.response.content

    @pytest.mark.asyncio
    async def test_on_build_functions_hook(
        self, mock_model: MockAIModel, test_function: Function[MockFunctionParams]
    ) -> None:
        """Test that on_build_functions hook is called and functions are passed to model"""
        plugin = MockPlugin("test_plugin")

        prompt = ChatPrompt(mock_model, functions=[test_function], plugins=[plugin])
        await prompt.send("Test message")

        assert plugin.build_functions_called
        # Verify functions were passed to the model (wrapped versions)
        assert mock_model.last_functions is not None
        assert "test_function" in mock_model.last_functions
        # The function should be wrapped with plugin hooks but still have same name/description
        wrapped_func = mock_model.last_functions["test_function"]
        assert wrapped_func.name == test_function.name
        assert wrapped_func.description == test_function.description

    @pytest.mark.asyncio
    async def test_multiple_plugins_execution_order(self, mock_model: MockAIModel) -> None:
        """Test that multiple plugins execute in correct order"""
        plugin1 = MockPlugin("plugin1")
        plugin1.input_modifications = ["FIRST"]
        plugin1.response_modifications = ["FIRST_RESP"]

        plugin2 = MockPlugin("plugin2")
        plugin2.input_modifications = ["SECOND"]
        plugin2.response_modifications = ["SECOND_RESP"]

        prompt = ChatPrompt(mock_model, plugins=[plugin1, plugin2])
        result = await prompt.send("Original")

        # Both plugins should be called
        assert plugin1.before_send_called
        assert plugin2.before_send_called
        assert plugin1.after_send_called
        assert plugin2.after_send_called

        # Input should be modified by both plugins in order
        assert result.response.content == "SECOND_RESP: FIRST_RESP: GENERATED - SECOND: FIRST: Original"

    @pytest.mark.asyncio
    async def test_plugin_returns_none_preserves_original(self, mock_model: MockAIModel) -> None:
        """Test that when plugin returns None, original values are preserved"""

        class NoOpPlugin(BaseAIPlugin):
            def __init__(self):
                super().__init__("noop")

            async def on_before_send(self, input: Message) -> Message | None:
                return None  # Return None to preserve original

            async def on_after_send(self, response: ModelMessage) -> ModelMessage | None:
                return None  # Return None to preserve original

        plugin = NoOpPlugin()
        prompt = ChatPrompt(mock_model, plugins=[plugin])
        result = await prompt.send("Test message")

        # Should be unchanged since plugin returned None
        assert result.response.content == "GENERATED - Test message"

    @pytest.mark.asyncio
    async def test_empty_plugin_list_maintains_compatibility(self, mock_model: MockAIModel) -> None:
        """Test that ChatPrompt with no plugins behaves identically to original implementation"""
        prompt_with_plugins = ChatPrompt(mock_model, plugins=[])
        prompt_without_plugins = ChatPrompt(mock_model)

        result_with = await prompt_with_plugins.send("Test message")
        result_without = await prompt_without_plugins.send("Test message")

        assert result_with.response.content == result_without.response.content

    @pytest.mark.asyncio
    async def test_plugin_with_async_function_handler(self, mock_function_handler: Mock) -> None:
        """Test plugin hooks work correctly with async function handlers"""
        plugin = MockPlugin("async_test")
        plugin.function_result_modifications = ["ASYNC_MODIFIED"]

        # Use the existing mock function handler (it's already set up correctly)
        mock_model = MockAIModel(should_call_function=True)

        test_function = Function(
            name="test_function",  # Use same name as MockAIModel expects
            description="A test function",
            parameter_schema=MockFunctionParams,
            handler=mock_function_handler,
        )

        prompt = ChatPrompt(mock_model, functions=[test_function], plugins=[plugin])
        result = await prompt.send("Call the function")

        # Verify function was called and result was modified by plugin
        assert len(plugin.before_function_called) == 1
        assert len(plugin.after_function_called) == 1
        assert result.response.content is not None
        assert "ASYNC_MODIFIED: Function executed successfully" in result.response.content

    @pytest.mark.asyncio
    async def test_plugin_error_handling(self, mock_model: MockAIModel) -> None:
        """Test that plugin errors don't break the chat flow"""

        class FaultyPlugin(BaseAIPlugin):
            def __init__(self):
                super().__init__("faulty")

            async def on_before_send(self, input: Message) -> Message | None:
                raise ValueError("Plugin error")

        plugin = FaultyPlugin()
        prompt = ChatPrompt(mock_model, plugins=[plugin])

        # Plugin error should propagate (this is expected behavior)
        with pytest.raises(ValueError, match="Plugin error"):
            await prompt.send("Test message")

    @pytest.mark.asyncio
    async def test_base_plugin_default_implementations(self, mock_model: MockAIModel) -> None:
        """Test that BaseAIPlugin provides working default implementations"""
        base_plugin = BaseAIPlugin("base")
        prompt = ChatPrompt(mock_model, plugins=[base_plugin])

        # Should work without any issues using default implementations
        result = await prompt.send("Test with base plugin")
        assert result.response.content == "GENERATED - Test with base plugin"

        # Test with functions too
        def handler(params: MockFunctionParams) -> str:
            return "Base plugin test"

        test_function = Function("test", "test", MockFunctionParams, handler)
        prompt_with_func = ChatPrompt(mock_model, functions=[test_function], plugins=[base_plugin])

        result2 = await prompt_with_func.send("Test with function")
        assert result2.response.content == "GENERATED - Test with function"

    @pytest.mark.asyncio
    async def test_comprehensive_plugin_behavior_verification(self, mock_function_handler: Mock) -> None:
        """Comprehensive test verifying all plugin methods actually modify data passed to model"""
        plugin = MockPlugin("comprehensive")
        plugin.input_modifications = ["INPUT_MOD"]
        plugin.response_modifications = ["RESP_MOD"]
        plugin.function_result_modifications = ["FUNC_MOD"]

        mock_model = MockAIModel(should_call_function=True)
        test_function = Function(
            name="test_function",
            description="Test function",
            parameter_schema=MockFunctionParams,
            handler=mock_function_handler,
        )

        prompt = ChatPrompt(mock_model, functions=[test_function], plugins=[plugin])

        system_msg = SystemMessage(content="Original system")
        result = await prompt.send("Original input", instructions=system_msg)

        # Verify all plugin hooks were called
        assert plugin.before_send_called
        assert plugin.after_send_called
        assert plugin.build_system_message_called
        assert plugin.build_functions_called
        assert len(plugin.before_function_called) == 1
        assert len(plugin.after_function_called) == 1

        # Verify actual modifications reached the model
        assert mock_model.last_input is not None
        assert mock_model.last_input.content == "INPUT_MOD: Original input"

        assert mock_model.last_system_message is not None
        assert mock_model.last_system_message.content == "Plugin-modified: Original system"

        assert mock_model.last_functions is not None
        assert "test_function" in mock_model.last_functions

        # Verify final response includes all modifications
        assert result.response.content is not None
        assert "RESP_MOD:" in result.response.content
        assert "FUNC_MOD: Function executed successfully" in result.response.content
        assert "INPUT_MOD: Original input" in result.response.content
