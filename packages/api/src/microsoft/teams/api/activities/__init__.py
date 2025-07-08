"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .activity import Activity as ActivityBase
from .command import CommandActivity, CommandResultActivity, CommandResultValue, CommandSendActivity, CommandSendValue
from .conversation import (
    ConversationActivity,
    ConversationChannelData,
    ConversationEventType,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EndOfConversationCode,
)
from .event import EventActivity
from .handoff import HandoffActivity
from .install_update import InstallUpdateActivity
from .invoke import InvokeActivity
from .message import MessageActivities
from .trace import TraceActivity
from .typing import TypingActivity

Activity = Annotated[
    Union[
        HandoffActivity,
        TraceActivity,
        TypingActivity,
        CommandActivity,
        ConversationActivity,
        MessageActivities,
        EventActivity,
        InvokeActivity,
        InstallUpdateActivity,
    ],
    Field(discriminator="type"),
]

ActivityParams = Union[str, Activity]

__all__ = [
    "Activity",
    "ActivityBase",
    "CommandSendActivity",
    "CommandResultActivity",
    "CommandSendValue",
    "CommandResultValue",
    "ConversationActivity",
    "ConversationUpdateActivity",
    "ConversationChannelData",
    "EndOfConversationActivity",
    "EndOfConversationCode",
    "EventActivity",
    "InstallUpdateActivity",
    "TypingActivity",
    "ConversationEventType",
]
