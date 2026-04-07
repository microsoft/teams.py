"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Any, Literal, Optional

from ...models import ActivityBase, ChannelData
from ...models.custom_base_model import CustomBaseModel

MessageEventType = Literal["undeleteMessage", "editMessage"]


class MessageUpdateChannelData(ChannelData):
    """Channel data specific to message update activities."""

    event_type: MessageEventType  # pyright: ignore [reportGeneralTypeIssues]
    """The type of event for message update."""


class _MessageUpdateBase(CustomBaseModel):
    """Base class containing shared message update activity fields (all Optional except type)."""

    type: Literal["messageUpdate"] = "messageUpdate"

    text: Optional[str] = None
    """The text content of the message."""

    speak: Optional[str] = None
    """The text to speak."""

    summary: Optional[str] = None
    """The text to display if the channel cannot render cards."""

    expiration: Optional[datetime] = None
    """
    The time at which the activity should be considered to be "expired"
    and should not be presented to the recipient.
    """

    value: Optional[Any] = None
    """A value that is associated with the activity."""

    channel_data: Optional[MessageUpdateChannelData] = None
    """Channel-specific data for message update events."""


class MessageUpdateActivity(_MessageUpdateBase, ActivityBase):
    """Output model for received message update activities with required fields and read-only properties."""

    text: str = ""  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """The text content of the message."""

    channel_data: MessageUpdateChannelData  # pyright: ignore [reportGeneralTypeIssues]
    """Channel-specific data for message update events."""
