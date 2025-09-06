"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict

from microsoft.teams.ai import Function
from pydantic import BaseModel, create_model


def get_function_schema(func: Function[BaseModel]) -> Dict[str, Any]:
    """
    Get JSON schema from a Function's parameter_schema.

    Handles both dict schemas and Pydantic model classes.
    """
    if isinstance(func.parameter_schema, dict):
        # Raw JSON schema - use as-is
        return func.parameter_schema.copy()
    else:
        # Pydantic model - convert to JSON schema
        return func.parameter_schema.model_json_schema()


def parse_function_arguments(func: Function[BaseModel], arguments: Dict[str, Any]) -> BaseModel:
    """
    Parse function arguments into a BaseModel instance.

    Handles both dict schemas and Pydantic model classes.
    """
    if isinstance(func.parameter_schema, dict):
        # For dict schemas, create a simple BaseModel dynamically
        DynamicModel = create_model("DynamicParams")
        return DynamicModel(**arguments)
    else:
        # For Pydantic model schemas, parse normally
        return func.parameter_schema(**arguments)
