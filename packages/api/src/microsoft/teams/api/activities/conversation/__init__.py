"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .conversation_update import ConversationChannelData, ConversationUpdateActivity, EventType
from .end_of_conversation import EndOfConversationActivity, EndOfConversationCode

ConversationActivity = Annotated[
    Union[ConversationUpdateActivity, EndOfConversationActivity], Field(discriminator="_type")
]

__all__ = [
    "EventType",
    "ConversationChannelData",
    "ConversationUpdateActivity",
    "EndOfConversationCode",
    "EndOfConversationActivity",
    "ConversationActivity",
]
