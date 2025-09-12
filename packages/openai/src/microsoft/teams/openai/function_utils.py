"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Union

from microsoft.teams.ai import Function
from pydantic import BaseModel, ConfigDict


def get_function_schema(func: Function[Any]) -> Dict[str, Any]:
    """
    Get JSON schema from a Function's parameter_schema.

    Handles both dict schemas and Pydantic model classes, converting
    them to the format expected by OpenAI function calling.

    Args:
        func: Function object with parameter schema

    Returns:
        Dictionary containing JSON schema for the function parameters
    """
    if func.parameter_schema is None:
        # No parameters - return empty schema
        return {"type": "object", "properties": {}}
    elif isinstance(func.parameter_schema, dict):
        # Raw JSON schema - use as-is
        return func.parameter_schema.copy()
    else:
        # Pydantic model - convert to JSON schema
        return func.parameter_schema.model_json_schema()


def parse_function_arguments(func: Function[Any], arguments: Dict[str, Any]) -> Union[BaseModel, None]:
    """
    Parse function arguments into a BaseModel instance.

    Handles both dict schemas and Pydantic model classes, creating
    appropriate BaseModel instances for function execution.

    Args:
        func: Function object with parameter schema
        arguments: Raw arguments from AI model function call

    Returns:
        BaseModel instance with validated and parsed arguments, or None for no-parameter functions
    """
    if func.parameter_schema is None:
        # No parameters expected - return None
        return None
    elif isinstance(func.parameter_schema, dict):
        # For dict schemas, create a simple BaseModel dynamically
        # Use a simple approach that works with any dict schema
        class DynamicParams(BaseModel):
            model_config = ConfigDict(extra="allow")
        
        return DynamicParams(**arguments)
    else:
        # For Pydantic model schemas, parse normally
        return func.parameter_schema(**arguments)
