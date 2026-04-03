"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .message import MessageActivity, MessageActivityInput
from .message_delete import MessageDeleteActivity, MessageDeleteChannelData
from .message_reaction import MessageReactionActivity, MessageReactionActivityInput
from .message_update import (
    MessageEventType,
    MessageUpdateActivity,
    MessageUpdateChannelData,
)

# Union type for all message activities
MessageActivities = Annotated[
    Union[
        MessageActivity,
        MessageDeleteActivity,
        MessageReactionActivity,
        MessageUpdateActivity,
    ],
    Field(discriminator="type"),
]

__all__ = [
    "MessageActivity",
    "MessageActivityInput",
    "MessageDeleteActivity",
    "MessageDeleteChannelData",
    "MessageReactionActivity",
    "MessageReactionActivityInput",
    "MessageUpdateActivity",
    "MessageUpdateChannelData",
    "MessageEventType",
]
