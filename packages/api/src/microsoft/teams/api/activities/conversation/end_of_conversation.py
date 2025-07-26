"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import ActivityBase, ActivityInputBase, CustomBaseModel

EndOfConversationCode = Literal[
    "unknown", "completedSuccessfully", "userCancelled", "botTimedOut", "botIssuedInvalidMessage", "channelFailed"
]


class _EndOfConversationBase(CustomBaseModel):
    """Base class containing shared end of conversation activity fields (all Optional except type)."""

    type: Literal["endOfConversation"] = "endOfConversation"

    code: Optional[EndOfConversationCode] = None
    """
    The code for endOfConversation activities that indicates why the conversation ended.
    Possible values include: 'unknown', 'completedSuccessfully', 'userCancelled', 'botTimedOut',
    'botIssuedInvalidMessage', 'channelFailed'
    """

    text: Optional[str] = None
    """The text content of the message."""


class EndOfConversationActivity(ActivityBase, _EndOfConversationBase):
    """Output model for received end of conversation activities with required fields and read-only properties."""

    text: str  # pyright: ignore [reportGeneralTypeIssues]
    """The text content of the message."""


class EndOfConversationActivityInput(ActivityInputBase, _EndOfConversationBase):
    """Input model for creating end of conversation activities with builder methods."""
