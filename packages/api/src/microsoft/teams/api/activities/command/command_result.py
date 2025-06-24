"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Generic, Literal, Optional, TypeVar

from ...models import CustomBaseModel
from ..activity import IActivity

T = TypeVar("T", bound=Any)


class CommandResultValue(CustomBaseModel, Generic[T]):
    """
    The value field of a ICommandResultActivity contains metadata related to a command result.
    An optional extensible data payload may be included if defined by the command activity name.
    The presence of an error field indicates that the original command failed to complete.
    """

    command_id: str
    """ID of the command."""

    data: Optional[T] = None
    """
    The data field containing optional parameters specific to this command activity,
    as defined by the name. The value of the data field is a complex type.
    """

    error: Optional[Exception] = None
    """The optional error, if the command result indicates a failure."""


class CommandResultActivity(IActivity[Literal["commandResult"]], CustomBaseModel, Generic[T]):
    """Asynchronous external command result."""

    name: str
    """The name of the event."""

    value: Optional[CommandResultValue[T]] = None
    """The value for this command."""
