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
from .handoff import HandoffActivity

Activity = Annotated[
    Union[HandoffActivity, CommandActivity, CommandResultActivity, ConversationActivity],
    Field(discriminator="_type"),
]

__all__ = [
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
