"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Literal

from ...models import ActivityBase, CustomBaseModel
from ..utils import input_model


class MeetingEndEventValue(CustomBaseModel):
    id: str
    """The meeting's Id, encoded as a BASE64 string."""

    meeting_type: str
    """Type of the meeting"""

    join_url: str
    """URL to join the meeting"""

    title: str
    """Title of the meeting."""

    end_time: datetime
    """Timestamp for meeting end, in UTC."""


class MeetingEndEventActivity(ActivityBase, CustomBaseModel):
    """
    Represents a meeting end event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  # pyright: ignore [reportIncompatibleVariableOverride]

    name: Literal["application/vnd.microsoft.meetingEnd"] = "application/vnd.microsoft.meetingEnd"

    value: MeetingEndEventValue


@input_model
class MeetingEndEventActivityInput(MeetingEndEventActivity):
    """
    Input type for MeetingEndEventActivity where ActivityBase fields are optional
    but event-specific fields retain their required status.
    """

    pass
