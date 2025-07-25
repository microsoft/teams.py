"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import ActivityBase, CustomBaseModel
from ..utils import input_model

EndOfConversationCode = Literal[
    "unknown", "completedSuccessfully", "userCancelled", "botTimedOut", "botIssuedInvalidMessage", "channelFailed"
]


class EndOfConversationActivity(ActivityBase, CustomBaseModel):
    """Activity for end of conversation events."""

    type: Literal["endOfConversation"] = "endOfConversation"  # pyright: ignore [reportIncompatibleVariableOverride]

    code: Optional[EndOfConversationCode] = None
    """
    The code for endOfConversation activities that indicates why the conversation ended.
    Possible values include: 'unknown', 'completedSuccessfully', 'userCancelled', 'botTimedOut',
    'botIssuedInvalidMessage', 'channelFailed'
    """

    text: str
    """The text content of the message."""


@input_model
class EndOfConversationActivityInput(EndOfConversationActivity):
    """
    Input type for EndOfConversationActivity where ActivityBase fields are optional
    but endOfConversation-specific fields retain their required status.
    """

    pass
