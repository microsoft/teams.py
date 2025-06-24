"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, TypeVar, Union

from .activity import Activity as ActivityBase
from .activity import IActivity
from .command import CommandActivity, CommandResultActivity, CommandResultValue, CommandValue
from .conversation import (
    ConversationActivity,
    ConversationChannelData,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EndOfConversationCode,
    EventType,
)
from .handoff import HandoffActivity

T = TypeVar("T", bound=Any)

Activity = Union[
    HandoffActivity,
    CommandActivity[T],
    CommandResultActivity[T],
    ConversationActivity,
]

__all__ = [
    "IActivity",
    "Activity",
    "ActivityBase",
    "CommandValue",
    "CommandActivity",
    "CommandResultValue",
    "CommandResultActivity",
    "ConversationUpdateActivity",
    "EndOfConversationActivity",
    "EndOfConversationCode",
    "EventType",
    "ConversationChannelData",
]
