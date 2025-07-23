"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ActivityBase, ChannelData


class MessageDeleteChannelData(ChannelData):
    """Channel data specific to message delete activities."""

    event_type: Literal["softDeleteMessage"] = "softDeleteMessage"
    """The type of event for message deletion."""


class MessageDeleteActivity(ActivityBase):
    """Represents a message delete activity in Microsoft Teams."""

    type: Literal["messageDelete"] = "messageDelete"

    channel_data: MessageDeleteChannelData  # pyright: ignore [reportGeneralTypeIssues]
    """Channel-specific data for message delete events."""
