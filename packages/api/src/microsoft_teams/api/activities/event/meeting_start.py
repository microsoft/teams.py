"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from ...models import ActivityBase, CustomBaseModel


class MeetingStartEventValue(CustomBaseModel):
    """
    The value associated with a meeting start event in Microsoft Teams.
    """

    id: str = Field(alias="Id")
    """
    The meeting's Id, encoded as a BASE64 string.
    """

    meeting_type: str = Field(alias="MeetingType")
    """
    Type of the meeting
    """

    join_url: str = Field(alias="JoinUrl")
    """
    URL to join the meetng
    """

    title: str = Field(alias="Title")
    """
    The title of the meeting
    """

    start_time: datetime = Field(alias="StartTime")
    """
    Timestamp for meeting start, in UTC.
    """


class MeetingStartEventActivity(ActivityBase, CustomBaseModel):
    """
    Represents a meeting start event activity in Microsoft Teams.
    """

    type: Literal["event"] = "event"  #

    name: Literal["application/vnd.microsoft.meetingStart"] = "application/vnd.microsoft.meetingStart"
    """
    The name of the operation associated with an invoke or event activity.
    """

    value: MeetingStartEventValue
    """
    The value of the event activity
    """
