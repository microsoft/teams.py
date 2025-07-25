"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import CustomBaseModel
from ..utils import input_model
from .meeting_participant import MeetingParticipantEventActivity


class MeetingParticipantJoinEventActivity(MeetingParticipantEventActivity, CustomBaseModel):
    name: Literal["application/vnd.microsoft.meetingParticipantJoin"] = (
        "application/vnd.microsoft.meetingParticipantJoin"
    )


@input_model
class MeetingParticipantJoinEventActivityInput(MeetingParticipantJoinEventActivity):
    """
    Input type for MeetingParticipantJoinEventActivity where ActivityBase fields are optional
    but event-specific fields retain their required status.
    """

    pass
