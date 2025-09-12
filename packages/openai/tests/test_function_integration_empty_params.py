"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock

import pytest
from microsoft.teams.ai import Function, FunctionCall, ModelMessage
from microsoft.teams.openai.completions_model import OpenAICompletionsAIModel
from microsoft.teams.openai.responses_chat_model import OpenAIResponsesAIModel
from pydantic import BaseModel


class FunctionTestParams(BaseModel):
    message: str


class TestFunctionIntegrationEmptyParams:
    """Integration tests for empty parameter functions with OpenAI models."""

    def test_no_param_function_definition(self):
        """Test that no-parameter functions can be defined properly."""

        def no_param_handler() -> str:
            return "no params needed"

        function = Function(
            name="test_no_params",
            description="A test function with no parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        assert function.parameter_schema is None
        assert function.handler == no_param_handler

    @pytest.mark.asyncio
    async def test_completions_model_function_execution_no_params(self):
        """Test function execution in completions model with no parameters."""

        def no_param_handler() -> str:
            return "executed successfully"

        function = Function(
            name="test_no_params",
            description="A test function with no parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        # Create mock client
        mock_client = AsyncMock()
        model = OpenAICompletionsAIModel(key="fake-key", model="gpt-4")
        model._client = mock_client

        # Simulate function call execution
        call = FunctionCall(id="call_123", name="test_no_params", arguments={})
        functions = {"test_no_params": function}

        # Test the function execution logic directly
        function_results = await model._execute_functions(ModelMessage(content="", function_calls=[call]), functions)

        assert len(function_results) == 1
        assert function_results[0].content == "executed successfully"
        assert function_results[0].function_id == "call_123"

    @pytest.mark.asyncio
    async def test_responses_model_function_execution_no_params(self):
        """Test function execution in responses model with no parameters."""

        def no_param_handler() -> str:
            return "responses model success"

        function = Function(
            name="test_no_params_responses",
            description="A test function with no parameters for responses model",
            parameter_schema=None,
            handler=no_param_handler,
        )

        # Create mock client
        mock_client = AsyncMock()
        model = OpenAIResponsesAIModel(key="fake-key", model="gpt-4")
        model._client = mock_client

        # Simulate function call execution
        call = FunctionCall(id="call_456", name="test_no_params_responses", arguments={})
        functions = {"test_no_params_responses": function}

        # Test the function execution logic directly
        function_results = await model._execute_functions(ModelMessage(content="", function_calls=[call]), functions)

        assert len(function_results) == 1
        assert function_results[0].content == "responses model success"
        assert function_results[0].function_id == "call_456"

    @pytest.mark.asyncio
    async def test_mixed_function_execution(self):
        """Test that models can handle both parameterized and no-parameter functions."""

        def no_param_handler() -> str:
            return "no params"

        def param_handler(params: FunctionTestParams) -> str:
            return f"got: {params.message}"

        no_param_function = Function(
            name="no_params", description="Function without parameters", parameter_schema=None, handler=no_param_handler
        )

        param_function = Function(
            name="with_params",
            description="Function with parameters",
            parameter_schema=FunctionTestParams,
            handler=param_handler,
        )

        # Create mock client
        mock_client = AsyncMock()
        model = OpenAICompletionsAIModel(key="fake-key", model="gpt-4")
        model._client = mock_client

        # Test both function types
        calls = [
            FunctionCall(id="call_1", name="no_params", arguments={}),
            FunctionCall(id="call_2", name="with_params", arguments={"message": "hello"}),
        ]
        functions = {"no_params": no_param_function, "with_params": param_function}

        function_results = await model._execute_functions(ModelMessage(content="", function_calls=calls), functions)

        assert len(function_results) == 2
        assert function_results[0].content == "no params"
        assert function_results[0].function_id == "call_1"
        assert function_results[1].content == "got: hello"
        assert function_results[1].function_id == "call_2"

    @pytest.mark.asyncio
    async def test_async_no_param_function_execution(self):
        """Test async function execution with no parameters."""

        async def async_no_param_handler() -> str:
            return "async no params"

        function = Function(
            name="async_no_params",
            description="Async function without parameters",
            parameter_schema=None,
            handler=async_no_param_handler,
        )

        # Create mock client
        mock_client = AsyncMock()
        model = OpenAICompletionsAIModel(key="fake-key", model="gpt-4")
        model._client = mock_client

        # Test async function execution
        call = FunctionCall(id="call_async", name="async_no_params", arguments={})
        functions = {"async_no_params": function}

        function_results = await model._execute_functions(ModelMessage(content="", function_calls=[call]), functions)

        assert len(function_results) == 1
        assert function_results[0].content == "async no params"
        assert function_results[0].function_id == "call_async"
