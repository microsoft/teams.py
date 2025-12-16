"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ...models import ActivityBase, ActivityInputBase, CustomBaseModel


class CommandSendValue(CustomBaseModel):
    """
    The value field of a CommandActivity contains metadata related to a command.
    An optional extensible data payload may be included if defined by the command activity name.
    """

    command_id: str
    """ID of the command."""

    data: Optional[Any] = None
    """
    The data field containing optional parameters specific to this command activity,
    as defined by the name. The value of the data field is a complex type.
    """


class _CommandSendBase(CustomBaseModel):
    """Base class containing shared command send activity fields (all Optional except type)."""

    type: Literal["command"] = "command"

    name: Optional[str] = None
    """The name of the event."""

    value: Optional[CommandSendValue] = None
    """The value for this command."""


class CommandSendActivity(_CommandSendBase, ActivityBase):
    """Output model for received command send activities with required fields and read-only properties."""

    name: str  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """The name of the event."""


class CommandSendActivityInput(_CommandSendBase, ActivityInputBase):
    """Input model for creating command send activities with builder methods."""

    pass
