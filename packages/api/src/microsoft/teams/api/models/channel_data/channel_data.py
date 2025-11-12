"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ..custom_base_model import CustomBaseModel
from ..meetings import MeetingInfo
from ..membership_source import MembershipSource
from .app_info import AppInfo
from .channel_info import ChannelInfo
from .notification_info import NotificationInfo
from .on_behalf_of import OnBehalfOf
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

    on_behalf_of: Optional[List[OnBehalfOf]] = None
    """Information about the users on behalf of whom the action is performed."""

    shared_with_teams: Optional[List[TeamInfo]] = None
    """List of teams that a channel was shared with."""

    unshared_from_teams: Optional[List[TeamInfo]] = None
    """List of teams that a channel was unshared from."""

    membership_source: Optional[MembershipSource] = None
    """Information about the source of the member that was added or removed froma shared channel."""

    app: Optional[AppInfo] = None
    """
    Information about the app sending this activity.
    """
