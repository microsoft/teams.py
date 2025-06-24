"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Generic, Literal, Optional, TypeVar

from ...models import CustomBaseModel
from ..activity import IActivity

T = TypeVar("T", bound=Any)


class CommandValue(CustomBaseModel, Generic[T]):
    """
    The value field of a ICommandActivity contains metadata related to a command.
    An optional extensible data payload may be included if defined by the command activity name.
    """

    command_id: str
    """ID of the command."""

    data: Optional[T] = None
    """
    The data field containing optional parameters specific to this command activity,
    as defined by the name. The value of the data field is a complex type.
    """


class CommandActivity(IActivity[Literal["command"]], CustomBaseModel, Generic[T]):
    """Send command activity."""

    name: str
    """The name of the event."""

    value: Optional[CommandValue[T]] = None
    """The value for this command."""
