"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field, TypeAdapter

from . import event, install_update, invoke, message
from .activity_params import ActivityParams
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
from .handoff import HandoffActivity
from .install_update import *  # noqa: F403
from .install_update import InstallUpdateActivity
from .invoke import *  # noqa: F403
from .invoke import InvokeActivity
from .message import *  # noqa: F403
from .message import MessageActivities
from .sent_activity import SentActivity
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

# Use this if you want to validate an incoming activity.
ActivityTypeAdapter = TypeAdapter[Activity](Activity)
ActivityTypeAdapter.rebuild()


# Combine all exports from submodules
__all__: list[str] = [
    "Activity",
    "ActivityTypeAdapter",
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
    "HandoffActivity",
    "InstallUpdateActivity",
    "TypingActivity",
    "ConversationEventType",
    "InvokeActivity",
    "TraceActivity",
    "ActivityParams",
    "SentActivity",
]
__all__.extend(event.__all__)
__all__.extend(install_update.__all__)
__all__.extend(message.__all__)
__all__.extend(invoke.__all__)
