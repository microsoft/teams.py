"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .conversation_update import ConversationChannelData, ConversationUpdateActivity, EventType
from .end_of_conversation import EndOfConversationActivity, EndOfConversationCode

ConversationActivity = Union[ConversationUpdateActivity, EndOfConversationActivity]

__all__ = [
    "EventType",
    "ConversationChannelData",
    "ConversationUpdateActivity",
    "EndOfConversationCode",
    "EndOfConversationActivity",
    "ConversationActivity",
]
