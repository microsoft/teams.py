"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Dict, Generic, Protocol, TypeVar, Union

from pydantic import BaseModel

Params = TypeVar("Params", bound=BaseModel, contravariant=True)
"""
Type variable for function parameter schemas.

Must be bound to BaseModel to ensure proper validation and serialization.
Contravariant to allow handlers to accept more general parameter types.
"""


class FunctionHandler(Protocol[Params]):
    """
    Protocol for function handlers that can be called by AI models.

    Function handlers can be either synchronous or asynchronous and should
    return a string result that will be passed back to the AI model.
    """

    def __call__(self, params: Params) -> Union[str, Awaitable[str]]:
        """
        Execute the function with the provided parameters.

        Args:
            params: Parsed and validated parameters for the function

        Returns:
            String result (sync) or awaitable string result (async)
        """
        ...


@dataclass
class Function(Generic[Params]):
    """
    Represents a function that can be called by AI models.

    Functions define the interface between AI models and external functionality,
    providing structured parameter validation and execution.

    Type Parameters:
        Params: Pydantic model class defining the function's parameter schema
    """

    name: str  # Unique identifier for the function
    description: str  # Human-readable description of what the function does
    parameter_schema: Union[type[Params], Dict[str, Any]]  # Pydantic model class or JSON schema dict
    handler: FunctionHandler[Params]  # Function implementation (sync or async)


@dataclass
class FunctionCall:
    """
    Represents a function call request from an AI model.

    Contains the function name, unique call ID, and parsed arguments
    that will be passed to the function handler.
    """

    id: str  # Unique identifier for this function call
    name: str  # Name of the function to call
    arguments: dict[str, Any]  # Parsed arguments for the function
