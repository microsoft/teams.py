"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .conversation_update import (
    ConversationChannelData,
    ConversationEventType,
    ConversationUpdateActivity,
    ConversationUpdateActivityInput,
)
from .end_of_conversation import EndOfConversationActivity, EndOfConversationActivityInput, EndOfConversationCode

ConversationActivity = Annotated[
    Union[ConversationUpdateActivity, EndOfConversationActivity], Field(discriminator="type")
]

__all__ = [
    "ConversationEventType",
    "ConversationChannelData",
    "ConversationUpdateActivity",
    "ConversationUpdateActivityInput",
    "EndOfConversationCode",
    "EndOfConversationActivity",
    "EndOfConversationActivityInput",
    "ConversationActivity",
]
