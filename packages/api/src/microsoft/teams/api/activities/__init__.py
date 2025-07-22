"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .command import CommandActivity, CommandResultActivity, CommandResultValue, CommandSendActivity, CommandSendValue
from .conversation import (
    ConversationActivity,
    ConversationChannelData,
    ConversationEventType,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EndOfConversationCode,
)
from .event import *  # noqa: F403
from .event import EventActivity
from .event import __all__ as event_all
from .handoff import HandoffActivity
from .install_update import *  # noqa: F403
from .install_update import InstallUpdateActivity
from .install_update import __all__ as install_update_all
from .invoke import InvokeActivity
from .message import *  # noqa: F403
from .message import MessageActivities
from .message import __all__ as message_all
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


__all__ = [
    "Activity",
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
    *event_all,
    *install_update_all,
    *message_all,
]
