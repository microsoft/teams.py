"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ...models import CustomBaseModel
from ..activity import Activity

EndOfConversationCode = Literal[
    "unknown", "completedSuccessfully", "userCancelled", "botTimedOut", "botIssuedInvalidMessage", "channelFailed"
]


class EndOfConversationActivity(Activity, CustomBaseModel):
    """Activity for end of conversation events."""

    _type: Literal["endOfConversation"] = "endOfConversation"

    @property
    def type(self) -> str:
        """The type of the activity."""
        return self._type

    code: Optional[EndOfConversationCode] = None
    """
    The code for endOfConversation activities that indicates why the conversation ended.
    Possible values include: 'unknown', 'completedSuccessfully', 'userCancelled', 'botTimedOut',
    'botIssuedInvalidMessage', 'channelFailed'
    """

    text: str
    """The text content of the message."""
