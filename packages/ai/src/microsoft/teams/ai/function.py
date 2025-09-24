"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Dict, Generic, Literal, Protocol, TypeVar, Union

from pydantic import BaseModel

Params = TypeVar("Params", bound=BaseModel, contravariant=True)
ResumableData = TypeVar("ResumableData")
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


class DeferredFunctionResumer(Generic[Params, ResumableData]):
    """
    The resumable function returns the actual string
    """

    def can_handle(self, activity: Any) -> bool:
        """
        Check if this resumer can handle the given activity input.

        Args:
            activity: The activity data to check

        Returns:
            True if this resumer can process the activity, False otherwise
        """
        ...

    def __call__(self, params: Params, resumableData: ResumableData) -> Awaitable[str]: ...


@dataclass
class DeferredResult:
    """
    Represents a deferred result that can be resumed later on
    """

    state: dict[str, Any]
    type: Literal["deferred"] = "deferred"


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


class DeferredFunctionHandler(Protocol[Params]):
    """
    The Deferred Function handler defers the job and returns the name
    of the resumable function
    Returns the name of the resumable function, and the parameters to save
    state
    """

    def __call__(self, params: Params) -> Awaitable[DeferredResult]: ...


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
    handler: FunctionHandler[Params] | DeferredFunctionHandler[Params]  # Function implementation (sync or async)
    resumer: DeferredFunctionResumer[Params, Any] | None = None  # Optional resumer for deferred functions
