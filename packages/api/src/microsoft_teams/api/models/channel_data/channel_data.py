"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, Self

from pydantic import model_validator

from ..custom_base_model import CustomBaseModel
from ..meetings import MeetingInfo
from .channel_info import ChannelInfo
from .feedback_loop import FeedbackLoop
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
    """
    Legacy feedback loop flag. Setting this to True is equivalent to feedback_loop=FeedbackLoop(type="default").
    Recommended to use feedback_loop directly. This field is normalized on model creation.
    """

    feedback_loop: Optional[FeedbackLoop] = None
    """
    Feedback loop configuration. Set type to 'custom' to show a task module dialog.
    Set to 'default' otherwise for standard feedback handling.
    """

    @model_validator(mode="after")
    def normalize_feedback(self) -> Self:
        """
        Normalize the feedback loop configuration.
        This is necessary as the client only accepts either/or.
        """
        if self.feedback_loop is not None:
            self.feedback_loop_enabled = None
        elif self.feedback_loop_enabled is True:
            self.feedback_loop = FeedbackLoop(type="default")
            self.feedback_loop_enabled = None
        return self

    stream_id: Optional[str] = None
    "ID of the stream. Assigned after the initial update is sent."

    stream_type: Optional[Literal["informative", "streaming", "final"]] = None
    "The type of message being sent."

    stream_sequence: Optional[int] = None
    """
    Sequence number of the message in the stream. Starts at 1 for the first message and
    increments from there.
    """
