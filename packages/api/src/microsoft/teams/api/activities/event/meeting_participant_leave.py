"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import CustomBaseModel
from ...utils import input_model
from .meeting_participant import MeetingParticipantEventActivity


class MeetingParticipantLeaveEventActivity(MeetingParticipantEventActivity, CustomBaseModel):
    name: Literal["application/vnd.microsoft.meetingParticipantLeave"] = (
        "application/vnd.microsoft.meetingParticipantLeave"
    )


@input_model
class MeetingParticipantLeaveEventActivityInput(MeetingParticipantLeaveEventActivity):
    """
    Input type for MeetingParticipantLeaveEventActivity where ActivityBase fields are optional
    but event-specific fields retain their required status.
    """

    pass
