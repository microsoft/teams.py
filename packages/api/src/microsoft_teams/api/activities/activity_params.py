"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Union of all activity input types (each defined next to their respective activities)
from typing import Annotated, Union

from pydantic import Field

from .command import CommandResultActivityInput, CommandSendActivityInput
from .conversation import ConversationUpdateActivityInput, EndOfConversationActivityInput
from .handoff import HandoffActivityInput
from .message import (
    MessageActivityInput,
    MessageDeleteActivityInput,
    MessageReactionActivityInput,
    MessageUpdateActivityInput,
)
from .trace import TraceActivityInput
from .typing import TypingActivityInput

ActivityParams = Annotated[
    Union[
        # Simple activities
        ConversationUpdateActivityInput,
        EndOfConversationActivityInput,
        HandoffActivityInput,
        TraceActivityInput,
        TypingActivityInput,
        # Message activities
        MessageActivityInput,
        MessageDeleteActivityInput,
        MessageReactionActivityInput,
        MessageUpdateActivityInput,
        # Command activities
        CommandSendActivityInput,
        CommandResultActivityInput,
    ],
    Field(discriminator="type"),
]
