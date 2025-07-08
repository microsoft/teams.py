"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .activity import Activity as ActivityBase
from .command import CommandActivity, CommandResultActivity, CommandResultValue, CommandValue
from .conversation import (
    ConversationActivity,
    ConversationChannelData,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EndOfConversationCode,
    EventType,
)
from .event import EventActivity
from .handoff import HandoffActivity
from .install_update import InstallUpdateActivity
from .trace import TraceActivity
from .typing import TypingActivity

Activity = Annotated[
    Union[
        EventActivity,
        TraceActivity,
        TypingActivity,
        HandoffActivity,
        CommandActivity,
        CommandResultActivity,
        ConversationActivity,
        InstallUpdateActivity,
    ],
    Field(discriminator="type"),
]

ActivityParams = Union[str, Activity]

__all__ = [
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
    "EventActivity",
    "InstallUpdateActivity",
    "TypingActivity",
    "ActivityParams",
]
