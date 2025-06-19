"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..account import Account, ConversationAccount
from ..custom_base_model import CustomBaseModel
from .meeting import Meeting


class MeetingParticipant(CustomBaseModel):
    """
    Teams meeting participant detailing user Azure Active Directory details.
    """

    user: Optional[Account] = None
    "The user details"

    meeting: Optional[Meeting] = None
    "The meeting details."

    conversation: Optional[ConversationAccount] = None
    "The conversation account for the meeting."
