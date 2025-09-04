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
    id: str | None = None
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


Message = Union[UserMessage, ModelMessage, SystemMessage, FunctionMessage]
