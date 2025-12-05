"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import CustomBaseModel
from .meeting_participant import MeetingParticipantEventActivity


class MeetingParticipantJoinEventActivity(MeetingParticipantEventActivity, CustomBaseModel):
    name: Literal["application/vnd.microsoft.meetingParticipantJoin"] = (
        "application/vnd.microsoft.meetingParticipantJoin"
    )
