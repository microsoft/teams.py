"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from ...models import ActivityBase, CustomBaseModel


class MeetingEndEventValue(CustomBaseModel):
    id: str = Field(alias="Id")
    """The meeting's Id, encoded as a BASE64 string."""

    meeting_type: str = Field(alias="MeetingType")
    """Type of the meeting"""

    join_url: Optional[str] = Field(default=None, alias="JoinUrl")
    """URL to join the meeting. Sent as null for meetings held inside a channel."""

    title: str = Field(alias="Title")
    """Title of the meeting."""

    end_time: datetime = Field(alias="EndTime")
    """Timestamp for meeting end, in UTC."""


class MeetingEndEventActivity(ActivityBase, CustomBaseModel):
    """
    Represents a meeting end event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  #

    name: Literal["application/vnd.microsoft.meetingEnd"] = "application/vnd.microsoft.meetingEnd"

    value: MeetingEndEventValue
