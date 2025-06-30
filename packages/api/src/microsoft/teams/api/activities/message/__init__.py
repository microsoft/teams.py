"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .message import MessageActivity
from .message_delete import MessageDeleteActivity, MessageDeleteChannelData
from .message_reaction import MessageReactionActivity
from .message_update import EventType, MessageUpdateActivity, MessageUpdateChannelData

# Union type for all message activities
MessageActivityUnion = Union[
    MessageActivity,
    MessageDeleteActivity,
    MessageReactionActivity,
    MessageUpdateActivity,
]

__all__ = [
    "MessageActivity",
    "MessageDeleteActivity",
    "MessageDeleteChannelData",
    "MessageReactionActivity",
    "MessageUpdateActivity",
    "MessageUpdateChannelData",
    "MessageActivityUnion",
    "EventType",
]
