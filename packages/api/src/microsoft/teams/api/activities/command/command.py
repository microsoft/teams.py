"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Optional

from ...models import CustomBaseModel
from ..activity import Activity


class CommandValue(CustomBaseModel):
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


class CommandActivity(Activity, CustomBaseModel):
    """Send command activity."""

    name: str
    """The name of the event."""

    value: Optional[CommandValue] = None
    """The value for this command."""
