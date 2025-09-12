"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.ai import Function
from microsoft.teams.openai.function_utils import get_function_schema, parse_function_arguments
from pydantic import BaseModel


class TestFunctionUtilsEmptyParams:
    """Test function utilities with empty parameters."""

    def test_get_function_schema_none_params(self):
        """Test get_function_schema with None parameter_schema."""

        def no_param_handler() -> str:
            return "success"

        function = Function(
            name="test_no_params",
            description="A test function with no parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        schema = get_function_schema(function)

        assert schema == {"type": "object", "properties": {}}

    def test_get_function_schema_with_params(self):
        """Test get_function_schema still works with parameters."""

        class TestParams(BaseModel):
            message: str

        def param_handler(params: TestParams) -> str:
            return f"Got: {params.message}"

        function = Function(
            name="test_with_params",
            description="A test function with parameters",
            parameter_schema=TestParams,
            handler=param_handler,
        )

        schema = get_function_schema(function)

        assert "type" in schema
        assert "properties" in schema
        assert "message" in schema["properties"]

    def test_parse_function_arguments_none_params(self):
        """Test parse_function_arguments with None parameter_schema."""

        def no_param_handler() -> str:
            return "success"

        function = Function(
            name="test_no_params",
            description="A test function with no parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        # Should return None when no parameters expected
        result = parse_function_arguments(function, {})
        assert result is None

        # Should still return None even if arguments are provided (they'll be ignored)
        result = parse_function_arguments(function, {"ignored": "value"})
        assert result is None

    def test_parse_function_arguments_with_params(self):
        """Test parse_function_arguments still works with parameters."""

        class TestParams(BaseModel):
            message: str

        def param_handler(params: TestParams) -> str:
            return f"Got: {params.message}"

        function = Function(
            name="test_with_params",
            description="A test function with parameters",
            parameter_schema=TestParams,
            handler=param_handler,
        )

        result = parse_function_arguments(function, {"message": "hello"})

        assert isinstance(result, TestParams)
        assert result.message == "hello"

    def test_parse_function_arguments_dict_schema(self):
        """Test parse_function_arguments with dict schema."""

        def dict_handler(params) -> str:
            return "success"

        function = Function(
            name="test_dict_schema",
            description="A test function with dict schema",
            parameter_schema={"type": "object", "properties": {"name": {"type": "string"}}},
            handler=dict_handler,
        )

        result = parse_function_arguments(function, {"name": "test"})

        # Should return a BaseModel instance even for dict schemas
        assert hasattr(result, "name")
        assert result.name == "test"
