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
from .event import *  # noqa: F403
from .event import __all__ as event_all
from .handoff import HandoffActivity
from .install_update import *  # noqa: F403
from .install_update import __all__ as install_update_all

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
    "CommandActivity",
    "CommandResultActivity",
    "CommandValue",
    "CommandResultValue",
    "ConversationActivity",
    "ConversationUpdateActivity",
    "ConversationChannelData",
    "EndOfConversationActivity",
    "EndOfConversationCode",
    "EventType",
    *event_all,
    *install_update_all,
]
