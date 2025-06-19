"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional

from ..account import Account, ConversationAccount
from ..custom_base_model import CustomBaseModel
from .meeting_details import MeetingDetails


class MeetingInfo(CustomBaseModel):
    """
    General information about a Teams meeting.
    """

    id: Optional[str] = None
    "Unique identifier representing a meeting"

    details: Optional[MeetingDetails] = None
    "The specific details of a Teams meeting."

    conversation: Optional[ConversationAccount] = None
    "The Conversation Account for the meeting."

    organizer: Optional[Account] = None
    "The organizer's user information."
