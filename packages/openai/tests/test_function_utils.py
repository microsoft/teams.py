"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Optional

import pytest
from microsoft.teams.ai import Function
from microsoft.teams.openai.function_utils import get_function_schema, parse_function_arguments
from pydantic import BaseModel, ValidationError


class SimpleParams(BaseModel):
    """Simple parameter model for testing."""

    name: str
    age: int


class OptionalParams(BaseModel):
    """Parameter model with optional fields."""

    required_field: str
    optional_field: Optional[str] = None


class EmptyParams(BaseModel):
    """Empty parameter model."""

    pass


def dummy_handler(params: BaseModel) -> str:
    """Dummy handler for testing."""
    return "test"


def dummy_handler_no_params() -> str:
    """Dummy handler with no params for testing."""
    return "test"


class TestGetFunctionSchema:
    """Tests for get_function_schema function."""

    def test_get_schema_from_pydantic_model(self):
        """Test getting schema from a Pydantic model."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=SimpleParams,
            handler=dummy_handler,
        )

        schema = get_function_schema(func)

        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "age" in schema["properties"]
        assert schema["properties"]["name"]["type"] == "string"
        assert schema["properties"]["age"]["type"] == "integer"

    def test_get_schema_from_dict(self):
        """Test getting schema from a dict."""
        dict_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "number"}},
            "required": ["param1"],
        }

        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=dict_schema,
            handler=dummy_handler,
        )

        schema = get_function_schema(func)

        assert schema == dict_schema
        # Ensure original is not modified
        assert schema is not dict_schema

    def test_get_schema_with_no_parameters(self):
        """Test getting schema when function has no parameters."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=None,
            handler=dummy_handler_no_params,
        )

        schema = get_function_schema(func)

        assert schema == {}


class TestParseFunctionArguments:
    """Tests for parse_function_arguments function."""

    def test_parse_with_pydantic_model(self):
        """Test parsing arguments with a Pydantic model schema."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=SimpleParams,
            handler=dummy_handler,
        )

        arguments = {"name": "John", "age": 30}
        result = parse_function_arguments(func, arguments)

        assert result is not None
        assert isinstance(result, SimpleParams)
        assert result.name == "John"
        assert result.age == 30

    def test_parse_with_pydantic_model_validation(self):
        """Test that Pydantic validation works correctly."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=SimpleParams,
            handler=dummy_handler,
        )

        # Invalid arguments (age should be int)
        arguments = {"name": "John", "age": "not_an_int"}

        with pytest.raises(ValidationError):
            parse_function_arguments(func, arguments)

    def test_parse_with_dict_schema_and_arguments(self):
        """Test parsing with dict schema and non-empty arguments."""
        dict_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "number"}},
        }

        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=dict_schema,
            handler=dummy_handler,
        )

        arguments = {"param1": "value1", "param2": 42}
        result = parse_function_arguments(func, arguments)

        assert result is not None
        assert isinstance(result, BaseModel)
        assert result.param1 == "value1"  # pyright: ignore
        assert result.param2 == 42  # pyright: ignore

    def test_parse_with_dict_schema_and_empty_arguments(self):
        """Test parsing with dict schema and empty arguments dict - BUG CASE."""
        dict_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
        }

        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=dict_schema,
            handler=dummy_handler,
        )

        # This is the bug case: empty arguments dict
        arguments = {}
        result = parse_function_arguments(func, arguments)

        assert result is not None
        assert isinstance(result, BaseModel)
        # The DynamicModel should handle empty args gracefully
        # Currently this may fail or behave unexpectedly

    def test_parse_with_no_parameter_schema(self):
        """Test parsing when function has no parameter schema."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=None,
            handler=dummy_handler_no_params,
        )

        arguments = {}
        result = parse_function_arguments(func, arguments)

        assert result is None

    def test_parse_with_optional_fields(self):
        """Test parsing with optional fields."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=OptionalParams,
            handler=dummy_handler,
        )

        # Only required field provided
        arguments = {"required_field": "test"}
        result = parse_function_arguments(func, arguments)

        assert result is not None
        assert isinstance(result, OptionalParams)
        assert result.required_field == "test"
        assert result.optional_field is None

    def test_parse_with_empty_pydantic_model(self):
        """Test parsing with an empty Pydantic model."""
        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=EmptyParams,
            handler=dummy_handler,
        )

        arguments = {}
        result = parse_function_arguments(func, arguments)

        assert result is not None
        assert isinstance(result, EmptyParams)

    def test_parse_preserves_dict_schema_immutability(self):
        """Test that parsing doesn't modify the original schema."""
        dict_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}},
        }
        original_schema = dict_schema.copy()

        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=dict_schema,
            handler=dummy_handler,
        )

        arguments = {"param1": "value1"}
        parse_function_arguments(func, arguments)

        # Ensure original schema unchanged
        assert func.parameter_schema == original_schema

    def test_parse_dict_schema_model_dump(self):
        """Test that model_dump() works correctly with dict schemas."""
        dict_schema = {
            "type": "object",
            "properties": {"param1": {"type": "string"}, "param2": {"type": "number"}},
        }

        func = Function(
            name="test_func",
            description="Test function",
            parameter_schema=dict_schema,
            handler=dummy_handler,
        )

        arguments = {"param1": "value1", "param2": 42}
        result = parse_function_arguments(func, arguments)

        assert result is not None
        # Verify model_dump() returns the arguments correctly
        dumped = result.model_dump()
        assert dumped == arguments
