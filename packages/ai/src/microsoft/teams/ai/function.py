"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
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


class FunctionHandlerWithNoParams(Protocol):
    """
    Protocol for function handlers that can be called by AI models.

    This handler does not have any parameters.

    Function handlers can be either synchronous or asynchronous and should
    return a string result that will be passed back to the AI model.
    """

    def __call__(self) -> Union[str, Awaitable[str]]:
        """
        Execute the function with no parameters.

        Returns:
            String result (sync) or awaitable string result (async)
        """
        ...


FunctionHandlers = Union[FunctionHandler[Any], FunctionHandlerWithNoParams]


@dataclass
class Function(Generic[Params]):
    """
    Represents a function that can be called by AI models.

    Functions define the interface between AI models and external functionality,
    providing structured parameter validation and execution.

    Type Parameters:
        Params: Pydantic model class defining the function's parameter schema, if any.

    Note:
        For best type safety, use explicit type parameters when creating Function objects:
        Function[SearchPokemonParams](name=..., parameter_schema=SearchPokemonParams, handler=...)

        This ensures the handler parameter type matches the parameter_schema at compile time.
    """

    name: str  # Unique identifier for the function
    description: str  # Human-readable description of what the function does
    parameter_schema: Union[type[Params], Dict[str, Any], None]  # Pydantic model class, JSON schema dict, or None
    handler: Union[FunctionHandler[Params], FunctionHandlerWithNoParams]  # Function implementation (sync or async)


@dataclass
class FunctionCall:
    """
    Represents a function call request from an AI model.

    Contains the function name, unique call ID, and parsed arguments
    that will be passed to the function handler if any.
    """

    id: str  # Unique identifier for this function call
    name: str  # Name of the function to call
    arguments: dict[str, Any] = field(default_factory=dict[str, Any])  # Parsed arguments for the function
