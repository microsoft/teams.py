"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Union of all activity input types (each defined next to their respective activities)
from typing import Annotated, Union

from pydantic import Field

from ..activities.command import CommandResultActivityInput, CommandSendActivityInput
from ..activities.conversation import ConversationUpdateActivityInput, EndOfConversationActivityInput
from ..activities.handoff import HandoffActivityInput
from ..activities.message import (
    MessageActivityInput,
    MessageDeleteActivityInput,
    MessageReactionActivityInput,
    MessageUpdateActivityInput,
)
from ..activities.trace import TraceActivityInput
from ..activities.typing import TypingActivityInput

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
        # Event activities
        # Install/Update activities
    ],
    Field(discriminator="type"),
]
