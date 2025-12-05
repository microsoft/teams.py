"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel
from ..meetings import MeetingInfo
from .channel_info import ChannelInfo
from .notification_info import NotificationInfo
from .settings import ChannelDataSettings
from .team_info import TeamInfo
from .tenant_info import TenantInfo


class ChannelData(CustomBaseModel):
    """
    Channel data specific to messages received in Microsoft Teams
    """

    channel: Optional[ChannelInfo] = None
    "Information about the channel in which the message was sent."

    event_type: Optional[str] = None
    "Type of event."

    team: Optional[TeamInfo] = None
    "Information about the team in which the message was sent."

    notification: Optional[NotificationInfo] = None
    "Notification settings for the message."

    tenant: Optional[TenantInfo] = None
    "Information about the tenant in which the message was sent."

    meeting: Optional[MeetingInfo] = None
    "Information about the tenant in which the message was sent."

    settings: Optional[ChannelDataSettings] = None
    "Information about the settings in which the message was sent."

    feedback_loop_enabled: Optional[bool] = None
    "Whether or not the feedback loop feature is enabled."

    stream_id: Optional[str] = None
    "ID of the stream. Assigned after the initial update is sent."

    stream_type: Optional[Literal["informative", "streaming", "final"]] = None
    "The type of message being sent."

    stream_sequence: Optional[int] = None
    """
    Sequence number of the message in the stream. Starts at 1 for the first message and
    increments from there.
    """
