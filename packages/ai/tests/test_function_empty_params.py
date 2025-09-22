"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft.teams.ai import Function
from pydantic import BaseModel


class TestEmptyParameterFunctions:
    """Test functions with no parameters."""

    def test_sync_function_no_params(self):
        """Test synchronous function with no parameters."""

        def no_param_handler() -> str:
            return "success"

        function = Function(
            name="test_no_params",
            description="A test function with no parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        assert function.name == "test_no_params"
        assert function.description == "A test function with no parameters"
        assert function.parameter_schema is None
        assert function.handler == no_param_handler

    @pytest.mark.asyncio
    async def test_async_function_no_params(self):
        """Test asynchronous function with no parameters."""

        async def async_no_param_handler() -> str:
            return "async success"

        function = Function(
            name="test_async_no_params",
            description="An async test function with no parameters",
            parameter_schema=None,
            handler=async_no_param_handler,
        )

        assert function.name == "test_async_no_params"
        assert function.description == "An async test function with no parameters"
        assert function.parameter_schema is None
        assert function.handler == async_no_param_handler

    def test_mixed_functions(self):
        """Test that we can have both parameterized and no-parameter functions."""

        class TestParams(BaseModel):
            message: str

        def param_handler(params: TestParams) -> str:
            return f"Got: {params.message}"

        def no_param_handler() -> str:
            return "No params needed"

        param_function = Function(
            name="with_params",
            description="Function with parameters",
            parameter_schema=TestParams,
            handler=param_handler,
        )

        no_param_function = Function(
            name="no_params",
            description="Function without parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        assert param_function.parameter_schema == TestParams
        assert no_param_function.parameter_schema is None
