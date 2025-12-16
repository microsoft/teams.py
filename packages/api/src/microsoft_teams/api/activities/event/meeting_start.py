"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Literal

from ...models import ActivityBase, CustomBaseModel


class MeetingStartEventValue(CustomBaseModel):
    """
    The value associated with a meeting start event in Microsoft Teams.
    """

    id: str
    """
    The meeting's Id, encoded as a BASE64 string.
    """

    meeting_type: str
    """
    Type of the meeting
    """

    join_url: str
    """
    URL to join the meeting
    """

    title: str
    """
    The title of the meeting
    """

    start_time: datetime
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
