"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TypeVar, Union

from .activity import Activity as ActivityBase
from .activity import IActivity
from .command import CommandActivity, CommandResultActivity, CommandResultValue, CommandSendActivity, CommandValue
from .conversation import (
    ConversationActivity,
    ConversationChannelData,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EndOfConversationCode,
    EventType,
)
from .handoff import HandoffActivity

T = TypeVar("T", bound=str)

Activity = Union[
    HandoffActivity,
    CommandSendActivity[T],
    CommandActivity[T],
    ConversationActivity,
]

__all__ = [
    "IActivity",
    "Activity",
    "ActivityBase",
    "CommandValue",
    "CommandSendActivity",
    "CommandResultValue",
    "CommandResultActivity",
    "ConversationUpdateActivity",
    "EndOfConversationActivity",
    "EndOfConversationCode",
    "EventType",
    "ConversationChannelData",
]
