"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..custom_base_model import CustomBaseModel
from .meeting import Meeting


# Placeholder for external types
class Account(CustomBaseModel):
    """Placeholder for Account model from ../account"""

    pass


class ConversationAccount(CustomBaseModel):
    """Placeholder for ConversationAccount model from ../account"""

    pass


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
