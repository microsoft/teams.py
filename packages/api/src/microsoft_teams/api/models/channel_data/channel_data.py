"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Self

from pydantic import model_validator

from ..custom_base_model import CustomBaseModel
from ..meetings import MeetingInfo
from ..stream_type import StreamType
from .app_info import AppInfo
from .channel_info import ChannelInfo
from .chat_info import ChatInfo
from .feedback_loop import FeedbackLoop
from .notification_info import NotificationInfo
from .reply_chain_info import ReplyChainInfo
from .settings import ChannelDataSettings
from .source_info import SourceInfo
from .team_info import TeamInfo
from .tenant_info import TenantInfo


class ChannelData(CustomBaseModel):
    """
    Channel data specific to messages received in Microsoft Teams
    """

    channel: Optional[ChannelInfo] = None
    "Information about the channel in which the message was sent."

    app: Optional[AppInfo] = None
    "Information about the app that sent the message."

    chat: Optional[ChatInfo] = None
    """
    Information about the chat scope that contains the activity.

    Present for activities in a 1:1 chat, a group chat or a meeting chat.
    Not sent for channels, where `channel` is used.
    `chat.id` is the chat's id without any reply chain (thread).
    Example: `19:<guid>_<guid>@unq.gbl.spaces` for a 1:1 chat, or `19:<id>@thread.v2` for a group chat.
    It can differ from `conversation.id`, which is opaque.
    Use it as the conversation id when sending a top-level message to the chat or replying in a reply chain.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

    reply_chain: Optional[ReplyChainInfo] = None
    """
    The reply chain (thread) the activity belongs to, identified by its root message.

    `reply_chain.id` is the id of the message at the root of the chain, for example `1793384051102`.
    For a top-level message it equals the message's own id. For a message in a thread it is the id of the thread's root.
    The SDK uses it, with `chat.id` or `channel.id`, to place a response in the thread.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

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

    source: Optional[SourceInfo] = None
    """
    Where the activity was fired or invoked from.

    Observed on activities from a card button (`name` is `message`), from feedback on a message (`message`),
    and from a compose extension action, including a message action, and the dialogs it opens (`compose`).
    The SDK treats a message that carries a non-empty `source.name` as sent by a card button.

    This API is in preview and may change in the future.
    Diagnostic: ExperimentalTeamsThreading
    """

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

    stream_type: Optional[StreamType] = None
    "The type of message being sent."

    stream_sequence: Optional[int] = None
    """
    Sequence number of the message in the stream. Starts at 1 for the first message and
    increments from there.
    """
