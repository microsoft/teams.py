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
)
from .conversation import (
    EventType as ConversationEventType,
)
from .event import *  # noqa: F403
from .event import __all__ as event_all
from .handoff import HandoffActivity
from .install_update import *  # noqa: F403
from .install_update import __all__ as install_update_all
from .message import (
    EventType as MessageEventType,
)
from .message import (
    MessageActivity,
    MessageDeleteActivity,
    MessageDeleteChannelData,
    MessageReactionActivity,
    MessageUpdateActivity,
    MessageUpdateChannelData,
)

Activity = Annotated[
    Union[
        HandoffActivity,
        CommandActivity,
        CommandResultActivity,
        ConversationActivity,
        MessageActivity,
        MessageDeleteActivity,
        MessageReactionActivity,
        MessageUpdateActivity,
    ],
    Field(discriminator="_type"),
]

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
    "ConversationEventType",
    "MessageEventType",
    "MessageActivity",
    "MessageDeleteActivity",
    "MessageDeleteChannelData",
    "MessageReactionActivity",
    "MessageUpdateActivity",
    "MessageUpdateChannelData",
    *event_all,
    *install_update_all,
]
