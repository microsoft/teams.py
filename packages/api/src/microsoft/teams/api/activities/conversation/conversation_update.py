"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List, Literal, Optional

from ...models import Account, ActivityBase, ActivityInputBase, ChannelData, CustomBaseModel

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

    event_type: Optional[ConversationEventType] = None
    """The type of event that occurred."""


class _ConversationUpdateBase(CustomBaseModel):
    """Base class containing shared conversation update activity fields (all Optional except type)."""

    type: Literal["conversationUpdate"] = "conversationUpdate"

    members_added: Optional[List[Account]] = None
    """The collection of members added to the conversation."""

    members_removed: Optional[List[Account]] = None
    """The collection of members removed from the conversation."""

    topic_name: Optional[str] = None
    """The updated topic name of the conversation."""

    history_disclosed: Optional[bool] = None
    """Indicates whether the prior history of the channel is disclosed."""

    channel_data: Optional[ConversationChannelData] = None
    """Channel data with event type information."""


class ConversationUpdateActivity(_ConversationUpdateBase, ActivityBase):
    """Output model for received conversation update activities with required fields and read-only properties."""

    channel_data: ConversationChannelData  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """Channel data with event type information."""


class ConversationUpdateActivityInput(_ConversationUpdateBase, ActivityInputBase):
    """Input model for creating conversation update activities with builder methods."""

    pass
