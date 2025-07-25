"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .meeting_end import MeetingEndEventActivity, MeetingEndEventActivityInput
from .meeting_participant import MeetingParticipantEventActivity
from .meeting_participant_join import MeetingParticipantJoinEventActivity, MeetingParticipantJoinEventActivityInput
from .meeting_participant_leave import MeetingParticipantLeaveEventActivity, MeetingParticipantLeaveEventActivityInput
from .meeting_start import MeetingStartEventActivity, MeetingStartEventActivityInput
from .read_reciept import ReadReceiptEventActivity, ReadReceiptEventActivityInput

EventActivity = Annotated[
    Union[
        ReadReceiptEventActivity,
        MeetingStartEventActivity,
        MeetingEndEventActivity,
        MeetingParticipantJoinEventActivity,
        MeetingParticipantLeaveEventActivity,
    ],
    Field(discriminator="name"),
]

EventActivityInput = Annotated[
    Union[
        ReadReceiptEventActivityInput,
        MeetingStartEventActivityInput,
        MeetingEndEventActivityInput,
        MeetingParticipantJoinEventActivityInput,
        MeetingParticipantLeaveEventActivityInput,
    ],
    Field(discriminator="name"),
]

__all__ = [
    "MeetingEndEventActivity",
    "MeetingEndEventActivityInput",
    "MeetingStartEventActivity",
    "MeetingStartEventActivityInput",
    "MeetingParticipantEventActivity",
    "MeetingParticipantJoinEventActivity",
    "MeetingParticipantJoinEventActivityInput",
    "MeetingParticipantLeaveEventActivity",
    "MeetingParticipantLeaveEventActivityInput",
    "ReadReceiptEventActivity",
    "ReadReceiptEventActivityInput",
    "EventActivity",
    "EventActivityInput",
]
