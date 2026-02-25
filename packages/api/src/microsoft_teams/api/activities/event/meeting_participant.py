"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ...models import ActivityBase, CustomBaseModel, TeamsChannelAccount


class MeetingParticipantInfo(CustomBaseModel):
    """
    Represents information about a participant in a Microsoft Teams meeting.
    """

    in_meeting: bool
    """Indicates whether the participant is currently in the meeting."""

    role: Optional[str] = None
    """The role of the participant in the meeting. Optional field."""


class MeetingParticipant(CustomBaseModel):
    """
    Represents a participant in a Microsoft Teams meeting.
    """

    user: TeamsChannelAccount
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

    type: Literal["event"] = "event"

    id: Optional[str] = None
    """Contains an ID that uniquely identifies the activity on the channel. Optional for meeting participant events."""

    value: MeetingParticipantEventValue
    """
    The value of the event.
    """
