"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ChannelData
from ..activity import Activity


class MessageDeleteChannelData(ChannelData):
    """Channel data specific to message delete activities."""

    event_type: Literal["softDeleteMessage"] = "softDeleteMessage"
    """The type of event for message deletion."""


class MessageDeleteActivity(Activity):
    """Represents a message delete activity in Microsoft Teams."""

    _type: Literal["messageDelete"] = "messageDelete"

    @property
    def type(self) -> str:
        """The type of the activity."""
        return self._type

    channel_data: MessageDeleteChannelData
    """Channel-specific data for message delete events."""
