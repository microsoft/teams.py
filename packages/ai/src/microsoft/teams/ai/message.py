"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Literal, Union

from .function import FunctionCall


@dataclass
class UserMessage:
    content: str
    role: Literal["user"] = "user"


@dataclass
class ModelMessage:
    content: str | None
    function_calls: list[FunctionCall] | None
    role: Literal["model"] = "model"


@dataclass
class SystemMessage:
    content: str
    role: Literal["system"] = "system"


@dataclass
class FunctionMessage:
    content: str | None
    function_id: str
    role: Literal["function"] = "function"


@dataclass
class ResponseIdMessage:
    """Special message type to store OpenAI Responses API response ID in memory."""

    response_id: str
    role: Literal["response_id"] = "response_id"


Message = Union[UserMessage, ModelMessage, SystemMessage, FunctionMessage, ResponseIdMessage]
