"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Optional

from ..custom_base_model import CustomBaseModel


class MeetingDetails(CustomBaseModel):
    """
    Meeting details including IDs and scheduling information.
    """

    id: str
    "The meeting's Id, encoded as a BASE64 string."

    type: str
    "The meeting's type."

    join_url: str
    "The URL used to join the meeting."

    title: str
    "The title of the meeting."

    ms_graph_resource_id: str
    "The MsGraphResourceId, used specifically for MS Graph API calls."

    scheduled_start_time: Optional[datetime] = None
    "The meeting's scheduled start time, in UTC."

    scheduled_end_time: Optional[datetime] = None
    "The meeting's scheduled end time, in UTC."
