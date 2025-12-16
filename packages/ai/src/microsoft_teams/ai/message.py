"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Literal, Union

from .function import FunctionCall


@dataclass
class UserMessage:
    """
    Represents a message from a user in the conversation.

    Contains the user's input text and is typically used as the starting
    point for AI model interactions.
    """

    content: str  # The user's message text
    role: Literal["user"] = "user"  # Message type identifier


@dataclass
class ModelMessage:
    """
    Represents a response from an AI model.

    Can contain either text content, function calls to be executed,
    or both. When function_calls is present, the content may be None.
    """

    content: str | None  # Generated text response (may be None if only function calls)
    function_calls: list[FunctionCall] | None  # Functions the model wants to call
    id: str | None = None  # Unique identifier for tracking (used in stateful APIs)
    role: Literal["model"] = "model"  # Message type identifier


@dataclass
class SystemMessage:
    """
    Represents system instructions or context for the AI model.

    Used to guide model behavior, provide context, or set up the
    conversation parameters without being part of the user dialogue.
    """

    content: str  # System instructions or context
    role: Literal["system"] = "system"  # Message type identifier


@dataclass
class FunctionMessage:
    """
    Represents the result of a function call execution.

    Contains the output from executing a function that was requested
    by the AI model, along with the function call ID for correlation.
    """

    content: str | None  # Function execution result (may be None on error)
    function_id: str  # ID correlating to the original FunctionCall
    role: Literal["function"] = "function"  # Message type identifier


Message = Union[UserMessage, ModelMessage, SystemMessage, FunctionMessage]
"""
Union type representing any message in a conversation.

Can be a user input, model response, system instruction, or function result.
Used throughout the AI framework for type-safe message handling.
"""
