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
    "channelShared",
    "channelUnshared",
    "channelMemberAdded",
    "channelMemberRemoved",
    "teamArchived",
    "teamDeleted",
    "teamHardDeleted",
    "teamRenamed",
    "teamRestored",
    "teamUnarchived",
    "teamMemberRemoved",
    "teamMemberAdded",
]


class ConversationChannelData(ChannelData, CustomBaseModel):
    """Extended ChannelData with event type."""

    event_type: Optional[str] = None
    """The type of event that occurred.

    Known values are enumerated by ``ConversationEventType``, but the field
    accepts any string so that unrecognized or newly introduced event types
    (e.g. from private/shared channels) do not fail validation.
    """


class _ConversationUpdateBase(CustomBaseModel):
    """Base class containing shared conversation update activity fields (all Optional except type)."""

    type: Literal["conversationUpdate"] = "conversationUpdate"

    members_added: Optional[List[Account]] = None
    """The collection of members added to the conversation."""

    members_removed: Optional[List[Account]] = None
    """The collection of members removed from the conversation."""

    topic_name: Optional[str] = None
    """The updated topic name of the conversation."""

    channel_data: Optional[ConversationChannelData] = None
    """Channel data with event type information."""


class ConversationUpdateActivity(_ConversationUpdateBase, ActivityBase):
    """Output model for received conversation update activities with read-only properties.

    Note: channel_data may be absent for some conversationUpdate payloads
    (e.g. Direct Line activities) and should be treated as optional.
    """

    channel_data: Optional[ConversationChannelData] = None
    """Channel data with event type information."""
