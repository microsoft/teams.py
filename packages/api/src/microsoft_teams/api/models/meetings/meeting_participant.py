"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..account import ConversationAccount, TeamsChannelAccount
from ..custom_base_model import CustomBaseModel
from .meeting import Meeting


class MeetingParticipant(CustomBaseModel):
    """
    Teams meeting participant detailing user Azure Active Directory details.
    Meeting participant details pertain to the user's info within the context
    of a Teams meeting, such as their role and presence status in the meeting.
    This is separate from their general user information, which is represented
    by the TeamsChannelAccount.
    """

    user: Optional[TeamsChannelAccount] = None
    "The user details"

    meeting: Optional[Meeting] = None
    "The meeting details pertaining to the user."

    conversation: Optional[ConversationAccount] = None
    "The conversation account for the meeting."
