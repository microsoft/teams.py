"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import ActivityBase, ActivityInputBase, ChannelData
from ...models.custom_base_model import CustomBaseModel


class MessageDeleteChannelData(ChannelData):
    """Channel data specific to message delete activities."""

    event_type: Literal["softDeleteMessage"] = "softDeleteMessage"  #
    """The type of event for message deletion."""


class _MessageDeleteBase(CustomBaseModel):
    """Base class containing shared message delete activity fields (all Optional except type)."""

    type: Literal["messageDelete"] = "messageDelete"

    channel_data: Optional[MessageDeleteChannelData] = None
    """Channel-specific data for message delete events."""


class MessageDeleteActivity(_MessageDeleteBase, ActivityBase):
    """Output model for received message delete activities with required fields and read-only properties."""

    channel_data: MessageDeleteChannelData  # pyright: ignore [reportGeneralTypeIssues]
    """Channel-specific data for message delete events."""


class MessageDeleteActivityInput(_MessageDeleteBase, ActivityInputBase):
    """Input model for creating message delete activities with builder methods."""
