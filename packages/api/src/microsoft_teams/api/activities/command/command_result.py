"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal, Optional

from ...models import ActivityBase, ActivityInputBase, CustomBaseModel


class CommandResultValue(CustomBaseModel):
    """
    The value field of a CommandResultActivity contains metadata related to a command result.
    An optional extensible data payload may be included if defined by the command activity name.
    The presence of an error field indicates that the original command failed to complete.
    """

    command_id: str
    """ID of the command."""

    data: Optional[Any] = None
    """
    The data field containing optional parameters specific to this command activity,
    as defined by the name. The value of the data field is a complex type.
    """

    error: Optional[Exception] = None
    """The optional error, if the command result indicates a failure."""


class _CommandResultBase(CustomBaseModel):
    """Base class containing shared command result activity fields (all Optional except type)."""

    type: Literal["commandResult"] = "commandResult"

    name: Optional[str] = None
    """The name of the event."""

    value: Optional[CommandResultValue] = None
    """The value for this command."""


class CommandResultActivity(_CommandResultBase, ActivityBase):
    """Output model for received command result activities with required fields and read-only properties."""

    name: str  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """The name of the event."""


class CommandResultActivityInput(_CommandResultBase, ActivityInputBase):
    """Input model for creating command result activities with builder methods."""

    pass
