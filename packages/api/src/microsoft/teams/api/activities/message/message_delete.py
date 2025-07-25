"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ActivityBase, ChannelData
from ..utils import input_model


class MessageDeleteChannelData(ChannelData):
    """Channel data specific to message delete activities."""

    event_type: Literal["softDeleteMessage"] = "softDeleteMessage"  # pyright: ignore [reportIncompatibleVariableOverride]
    """The type of event for message deletion."""


class MessageDeleteActivity(ActivityBase):
    """Represents a message delete activity in Microsoft Teams."""

    type: Literal["messageDelete"] = "messageDelete"  # pyright: ignore [reportIncompatibleVariableOverride]

    channel_data: MessageDeleteChannelData  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """Channel-specific data for message delete events."""


@input_model
class MessageDeleteActivityInput(MessageDeleteActivity):
    """
    Input type for MessageDeleteActivity where ActivityBase fields are optional
    but messageDelete-specific fields retain their required status.
    """

    pass
