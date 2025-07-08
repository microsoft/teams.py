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
    ConversationEventType,
    ConversationUpdateActivity,
    EndOfConversationActivity,
    EndOfConversationCode,
)
from .event import EventActivity
from .handoff import HandoffActivity
from .install_update import InstallUpdateActivity
from .message import *  # noqa: F403
from .message import (
    MessageActivities,
)
from .message import (
    __all__ as message_all,
)
from .trace import TraceActivity
from .typing import TypingActivity

Activity = Annotated[
    Union[
        HandoffActivity,
        TraceActivity,
        TypingActivity,
        CommandActivity,
        CommandResultActivity,
        ConversationActivity,
        MessageActivities,
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
    "EventActivity",
    "InstallUpdateActivity",
    "TypingActivity",
    "ActivityParams",
    "ConversationEventType",
    *message_all,
]
