"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .conversation_update import (
    ConversationChannelData,
    ConversationEventType,
    ConversationUpdateActivity,
)

ConversationActivity = ConversationUpdateActivity

__all__ = [
    "ConversationEventType",
    "ConversationChannelData",
    "ConversationUpdateActivity",
    "ConversationActivity",
]
