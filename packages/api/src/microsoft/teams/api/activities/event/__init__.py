"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .meeting_end import MeetingEndEventActivity
from .meeting_participant import MeetingParticipantEventActivity
from .meeting_participant_join import MeetingParticipantJoinEventActivity
from .meeting_participant_leave import MeetingParticipantLeaveEventActivity
from .meeting_start import MeetingStartEventActivity
from .read_reciept import ReadReceiptEventActivity

EventActivity = Union[
    ReadReceiptEventActivity,
    MeetingStartEventActivity,
    MeetingEndEventActivity,
    MeetingParticipantJoinEventActivity,
    MeetingParticipantLeaveEventActivity,
]

__all__ = [
    "MeetingEndEventActivity",
    "MeetingStartEventActivity",
    "MeetingParticipantEventActivity",
    "MeetingParticipantJoinEventActivity",
    "MeetingParticipantLeaveEventActivity",
    "ReadReceiptEventActivity",
    "EventActivity",
]
