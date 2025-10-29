"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Optional

from microsoft.teams.ai import Function
from pydantic import BaseModel, ConfigDict, create_model


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
    if not func.parameter_schema:
        # No parameters case
        return {}

    if isinstance(func.parameter_schema, dict):
        # Raw JSON schema - use as-is
        return func.parameter_schema.copy()
    else:
        # Pydantic model - convert to JSON schema
        return func.parameter_schema.model_json_schema()


def parse_function_arguments(func: Function[Any], arguments: Dict[str, Any]) -> Optional[BaseModel]:
    """
    Parse function arguments into a BaseModel instance.

    Handles both dict schemas and Pydantic model classes, creating
    appropriate BaseModel instances for function execution.

    Args:
        func: Function object with parameter schema
        arguments: Raw arguments from AI model function call

    Returns:
        BaseModel instance with validated and parsed arguments
    """
    if not func.parameter_schema:
        return None

    if isinstance(func.parameter_schema, dict):
        # For dict schemas, create a simple BaseModel dynamically
        # Use extra='allow' to accept arbitrary fields from the arguments dict
        DynamicModel = create_model("DynamicParams", __config__=ConfigDict(extra="allow"))
        return DynamicModel(**arguments)
    else:
        # For Pydantic model schemas, parse normally
        return func.parameter_schema(**arguments)
