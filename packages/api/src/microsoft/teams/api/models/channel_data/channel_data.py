from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from .channel_info import ChannelInfo
from .notification_info import NotificationInfo
from .settings import ChannelDataSettings
from .team_info import TeamInfo
from .tenant_info import TenantInfo


class MeetingInfo(BaseModel):
    """Placeholder for MeetingInfo model from ../meeting"""

    pass


class ChannelData(BaseModel):
    """
    Channel data specific to messages received in Microsoft Teams
    """

    channel: Optional[ChannelInfo] = Field(
        None, description="Information about the channel in which the message was sent."
    )

    event_type: Optional[Any] = Field(None, alias="eventType", description="Type of event.")
    team: Optional[TeamInfo] = Field(None, description="Information about the team in which the message was sent.")
    notification: Optional[NotificationInfo] = Field(None, description="Notification settings for the message.")
    tenant: Optional[TenantInfo] = Field(
        None, description="Information about the tenant in which the message was sent."
    )
    meeting: Optional[MeetingInfo] = Field(
        None, description="Information about the tenant in which the message was sent."
    )
    settings: Optional[ChannelDataSettings] = Field(
        None, description="Information about the settings in which the message was sent."
    )
    feedback_loop_enabled: Optional[bool] = Field(
        None, alias="feedbackLoopEnabled", description="Whether or not the feedback loop feature is enabled."
    )
    stream_id: Optional[str] = Field(
        None, alias="streamId", description="ID of the stream. Assigned after the initial update is sent."
    )
    stream_type: Optional[Literal["informative", "streaming", "final"]] = Field(
        None, alias="streamType", description="The type of message being sent."
    )
    stream_sequence: Optional[int] = Field(
        None,
        alias="streamSequence",
        description="Sequence number of the message in the stream. Starts at 1 for the first message and "
        + "increments from there.",
    )
