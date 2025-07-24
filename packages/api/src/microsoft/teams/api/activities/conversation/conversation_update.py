"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ...models import Account, ActivityBase, ChannelData, CustomBaseModel

ConversationEventType = Literal[
    "channelCreated",
    "channelDeleted",
    "channelRenamed",
    "channelRestored",
    "teamArchived",
    "teamDeleted",
    "teamHardDeleted",
    "teamRenamed",
    "teamRestored",
    "teamUnarchived",
]


class ConversationChannelData(ChannelData, CustomBaseModel):
    """Extended ChannelData with event type."""

    event_type: ConversationEventType  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """The type of event that occurred."""


class ConversationUpdateActivity(ActivityBase, CustomBaseModel):
    """Activity for conversation updates."""

    type: Literal["conversationUpdate"] = "conversationUpdate"  # pyright: ignore[reportIncompatibleVariableOverride]

    members_added: Optional[List[Account]] = None
    """The collection of members added to the conversation."""

    members_removed: Optional[List[Account]] = None
    """The collection of members removed from the conversation."""

    topic_name: Optional[str] = None
    """The updated topic name of the conversation."""

    history_disclosed: Optional[bool] = None
    """Indicates whether the prior history of the channel is disclosed."""

    channel_data: ConversationChannelData  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """Channel data with event type information."""
