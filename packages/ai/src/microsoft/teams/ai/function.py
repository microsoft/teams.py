"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Dict, Generic, Protocol, TypeVar, Union

from pydantic import BaseModel

Params = TypeVar("Params", bound=BaseModel, contravariant=True)


class FunctionHandler(Protocol[Params]):
    def __call__(self, params: Params) -> Union[str, Awaitable[str]]: ...


@dataclass
class Function(Generic[Params]):
    name: str
    description: str
    parameter_schema: Union[type[Params], Dict[str, Any]]
    handler: FunctionHandler[Params]


@dataclass
class FunctionCall:
    id: str
    name: str
    arguments: dict[str, Any]
