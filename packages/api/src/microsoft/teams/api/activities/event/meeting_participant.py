"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal

from ...models import Account, ActivityBase, CustomBaseModel


class MeetingParticipantInfo(CustomBaseModel):
    """
    Represents information about a participant in a Microsoft Teams meeting.
    """

    in_meeting: bool
    """Indicates whether the participant is currently in the meeting."""

    role: str
    """The role of the participant in the meeting"""


class MeetingParticipant(CustomBaseModel):
    """
    Represents a participant in a Microsoft Teams meeting.
    """

    user: Account
    """The participant account."""

    meeting: MeetingParticipantInfo
    """The participant's info"""


class MeetingParticipantEventValue(CustomBaseModel):
    members: List[MeetingParticipant]
    """The list of participants in the meeting."""


class MeetingParticipantEventActivity(ActivityBase, CustomBaseModel):
    """
    Represents a meeting participant event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  #

    value: MeetingParticipantEventValue
    """
    The value of the event.
    """
