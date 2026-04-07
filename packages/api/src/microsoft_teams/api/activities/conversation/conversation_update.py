"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Literal, Optional

from pydantic import model_validator

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
    "teamMemberRemoved",
    "teamMemberAdded",
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

    channel_data: Optional[ConversationChannelData] = None
    """Channel data with event type information."""


class ConversationUpdateActivity(_ConversationUpdateBase, ActivityBase):
    """Output model for received conversation update activities with required fields and read-only properties.

    Design note (channel_data field):
        In Teams, conversationUpdate activities always include channelData with an eventType
        discriminator (e.g. "channelCreated", "teamArchived"). The routing system
        (activity_route_configs.py) relies on channel_data.event_type to dispatch to specific
        handlers like on_channel_created() and on_team_archived().

        However, non-Teams channels (notably Direct Line) send conversationUpdate activities
        WITHOUT channelData, which would cause a Pydantic ValidationError if the field were
        strictly required. See https://github.com/microsoft/teams.py/issues/239.

        Resolution: We keep channel_data as a REQUIRED field (preserving the type contract for
        the 99% of developers building Teams bots) but add a model_validator that defaults it to
        an empty ConversationChannelData() when missing from the incoming payload. This matches
        the TypeScript SDK pattern, where the type declares channelData as required on
        IConversationUpdateActivity (conversation-update.ts:25) but the router uses optional
        chaining defensively (router.ts:73-87).

        The empty default means:
        - Teams activities: channel_data is populated normally, event_type routes work as before
        - Direct Line activities: channel_data is an empty ConversationChannelData (event_type=None),
          so Teams-specific event handlers don't fire, but the generic on_conversation_update()
          handler still does
        - Type checkers see a non-optional ConversationChannelData — no None-guards needed
    """

    channel_data: ConversationChannelData  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """Channel data with event type information. Always present — defaulted to empty for non-Teams channels."""

    @model_validator(mode="before")
    @classmethod
    def _default_channel_data(cls, data: Any) -> Any:
        """Supply an empty channelData when absent (e.g. Direct Line).

        Without this, Pydantic rejects the payload because channel_data is required.
        The empty default preserves the required-field contract for Teams developers
        while allowing non-Teams channels to send conversationUpdate without channelData.
        See: https://github.com/microsoft/teams.py/issues/239
        """
        if isinstance(data, dict):
            # Check both the snake_case field name and the camelCase alias
            if "channel_data" not in data and "channelData" not in data:
                data["channelData"] = {}
        return data


class ConversationUpdateActivityInput(_ConversationUpdateBase, ActivityInputBase):
    """Input model for creating conversation update activities with builder methods."""

    pass
