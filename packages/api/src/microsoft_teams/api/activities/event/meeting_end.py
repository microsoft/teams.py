"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Literal

from ...models import ActivityBase, CustomBaseModel


class MeetingEndEventValue(CustomBaseModel):
    Id: str
    """The meeting's Id, encoded as a BASE64 string."""

    MeetingType: str
    """Type of the meeting"""

    JoinUrl: str
    """URL to join the meeting"""

    Title: str
    """Title of the meeting."""

    EndTime: datetime
    """Timestamp for meeting end, in UTC."""


class MeetingEndEventActivity(ActivityBase, CustomBaseModel):
    """
    Represents a meeting end event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  #

    name: Literal["application/vnd.microsoft.meetingEnd"] = "application/vnd.microsoft.meetingEnd"

    value: MeetingEndEventValue
