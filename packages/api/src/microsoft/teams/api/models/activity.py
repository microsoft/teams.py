"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Any, List, Optional, Self

from microsoft.teams.api.models.account import Account, ConversationAccount
from microsoft.teams.api.models.channel_data.channel_data import ChannelData
from microsoft.teams.api.models.channel_data.channel_info import ChannelInfo
from microsoft.teams.api.models.channel_data.notification_info import NotificationInfo
from microsoft.teams.api.models.channel_data.team_info import TeamInfo
from microsoft.teams.api.models.channel_id import ChannelID
from microsoft.teams.api.models.conversation.conversation_reference import ConversationReference
from microsoft.teams.api.models.entity.ai_message_entity import AIMessageEntity
from microsoft.teams.api.models.entity.citation_entity import (
    Appearance,
    CitationAppearance,
    CitationEntity,
    Claim,
    Image,
)
from microsoft.teams.api.models.entity.entity import Entity
from microsoft.teams.api.models.entity.message_entity import MessageEntity
from microsoft.teams.api.models.meetings.meeting_info import MeetingInfo

from .custom_base_model import CustomBaseModel


class _ActivityBase(CustomBaseModel):
    """Base class containing shared activity fields."""

    service_url: Optional[str] = None
    """Contains the URL that specifies the channel's service endpoint. Set by the channel."""

    timestamp: Optional[datetime] = None
    """Contains the date and time that the message was sent, in UTC, expressed in ISO-8601 format."""

    locale: Optional[str] = None
    """
    A locale name for the contents of the text field.
    The locale name is a combination of an ISO 639 two- or three-letter culture code associated
    with a language and an ISO 3166 two-letter subculture code associated with a country or region.
    The locale name can also correspond to a valid BCP-47 language tag.
    """

    local_timestamp: Optional[datetime] = None
    """
    Contains the local date and time of the message, expressed in ISO-8601 format.
    For example, 2016-09-23T13:07:49.4714686-07:00.
    """

    channel_id: ChannelID = "msteams"
    """Contains an ID that uniquely identifies the channel. Set by the channel."""

    from_: Account
    """Identifies the sender of the message."""

    conversation: ConversationAccount
    """Identifies the conversation to which the activity belongs."""

    relates_to: Optional[ConversationReference] = None
    """A reference to another conversation or activity."""

    reply_to_id: Optional[str] = None
    """Contains the ID of the message to which this message is a reply."""

    entities: Optional[List[Entity]] = None
    """Represents the entities that were mentioned in the message."""

    channel_data: Optional[ChannelData] = None
    """Contains channel-specific content."""


class ActivityInput(_ActivityBase):
    """Input model for creating activities with builder methods."""

    type: Optional[str] = None
    """Contains the type of the activity."""

    id: Optional[str] = None
    """Contains an ID that uniquely identifies the activity on the channel."""

    channel_id: Optional[ChannelID] = None
    """Contains an ID that uniquely identifies the channel. Set by the channel."""

    from_: Optional[Account] = None
    """Identifies the sender of the message."""

    conversation: Optional[ConversationAccount] = None
    """Identifies the conversation to which the activity belongs."""

    recipient: Optional[Account] = None
    """Identifies the recipient of the message."""

    @property
    def channel(self) -> Optional[ChannelInfo]:
        """Information about the channel in which the message was sent."""
        return self.channel_data.channel if self.channel_data else None

    @property
    def team(self) -> Optional[TeamInfo]:
        """Information about the team in which the message was sent."""
        return self.channel_data.team if self.channel_data else None

    @property
    def meeting(self) -> Optional[MeetingInfo]:
        """Information about the tenant in which the message was sent."""
        return self.channel_data.meeting if self.channel_data else None

    @property
    def notification(self) -> Optional[NotificationInfo]:
        """Notification settings for the message."""
        return self.channel_data.notification if self.channel_data else None

    @property
    def tenant(self) -> Any:
        """Information about the tenant in which the message was sent."""
        return self.channel_data.tenant if self.channel_data else None

    def with_id(self, value: str) -> Self:
        """Set the id."""
        self.id = value
        return self

    def with_reply_to_id(self, value: str) -> Self:
        """Set the reply_to_id."""
        self.reply_to_id = value
        return self

    def with_channel_id(self, value: ChannelID) -> Self:
        """Set the channel_id."""
        self.channel_id = value
        return self

    def with_from(self, value: Account) -> Self:
        """Set the from field."""
        self.from_ = value
        return self

    def with_conversation(self, value: ConversationAccount) -> Self:
        """Set the conversation."""
        self.conversation = value
        return self

    def with_relates_to(self, value: ConversationReference) -> Self:
        """Set the relates_to field."""
        self.relates_to = value
        return self

    def with_recipient(self, value: Account) -> Self:
        """Set the recipient."""
        self.recipient = value
        return self

    def with_service_url(self, value: str) -> Self:
        """Set the service_url."""
        self.service_url = value
        return self

    def with_timestamp(self, value: datetime) -> Self:
        """Set the timestamp."""
        self.timestamp = value
        return self

    def with_locale(self, value: str) -> Self:
        """Set the locale."""
        self.locale = value
        return self

    def with_local_timestamp(self, value: datetime) -> Self:
        """Set the local_timestamp."""
        self.local_timestamp = value
        return self

    def with_channel_data(self, value: ChannelData) -> Self:
        """Set or update channel_data."""
        if not self.channel_data:
            self.channel_data = value
        else:
            data = {**self.channel_data.model_dump(), **value.model_dump()}
            self.channel_data = ChannelData(**data)
        return self

    def add_entity(self, value: Entity) -> Self:
        """Add an entity."""
        if not self.entities:
            self.entities = []
        self.entities.append(value)
        return self

    def add_entities(self, *values: Entity) -> Self:
        """Add multiple entities."""
        if not self.entities:
            self.entities = []
        self.entities.extend(values)
        return self

    def add_ai_generated(self) -> Self:
        """Add the 'Generated By AI' label."""
        message_entity = self.ensure_single_root_level_message_entity()
        ai_entity = AIMessageEntity(**message_entity.model_dump())
        if ai_entity.additional_type and "AIGeneratedContent" in ai_entity.additional_type:
            return self

        if not ai_entity.additional_type:
            ai_entity.additional_type = []

        ai_entity.additional_type.append("AIGeneratedContent")

        self._update_entity(message_entity, ai_entity)

        return self

    def add_feedback(self) -> Self:
        """Enable message feedback."""
        if not self.channel_data:
            self.channel_data = ChannelData(feedback_loop_enabled=True)
        else:
            self.channel_data.feedback_loop_enabled = True
        return self

    def add_citation(self, position: int, appearance: CitationAppearance) -> Self:
        """Add citations."""
        message_entity = self.ensure_single_root_level_message_entity()
        citation_entity = CitationEntity(**message_entity.model_dump())
        if citation_entity.citation is None:
            citation_entity.citation = []

        citation_entity.citation.append(
            Claim(
                position=position,
                appearance=Appearance(
                    abstract=appearance.abstract,
                    name=appearance.name,
                    image=Image(name=appearance.icon) if appearance.icon else None,
                    keywords=appearance.keywords,
                    text=appearance.text,
                    url=appearance.url,
                    usage_info=appearance.usage_info,
                ),
            )
        )

        self._update_entity(message_entity, citation_entity)

        return self

    def is_streaming(self) -> bool:
        """Check if this is a streaming activity."""
        return bool(self.entities and any(e.type == "streaminfo" for e in self.entities or []))

    def ensure_single_root_level_message_entity(self) -> MessageEntity:
        """
        Get or create the base message entity.
        There should only be one root level message entity.
        """
        message_entity = next(
            (e for e in (self.entities or []) if e.type == "https://schema.org/Message" and e.at_type == "Message"),
            None,
        )

        if not message_entity:
            message_entity = MessageEntity()
            self.add_entity(message_entity)

        return message_entity

    def _update_entity(self, old_entity: Entity, new_entity: Entity) -> None:
        if self.entities is not None:
            index = self.entities.index(old_entity)
            self.entities.pop(index)
            self.entities.insert(index, new_entity)


class Activity(_ActivityBase):
    """Output model for received activities with required fields and read-only properties."""

    type: str
    """Contains the type of the activity."""

    id: str
    """Contains an ID that uniquely identifies the activity on the channel."""

    channel_id: ChannelID = "msteams"
    """Contains an ID that uniquely identifies the channel. Set by the channel."""

    from_: Account
    """Identifies the sender of the message."""

    conversation: ConversationAccount
    """Identifies the conversation to which the activity belongs."""

    recipient: Account
    """Identifies the recipient of the message."""

    @property
    def channel(self) -> Optional[ChannelInfo]:
        """Information about the channel in which the message was sent."""
        return self.channel_data.channel if self.channel_data else None

    @property
    def team(self) -> Optional[TeamInfo]:
        """Information about the team in which the message was sent."""
        return self.channel_data.team if self.channel_data else None

    @property
    def meeting(self) -> Optional[MeetingInfo]:
        """Information about the tenant in which the message was sent."""
        return self.channel_data.meeting if self.channel_data else None

    @property
    def notification(self) -> Optional[NotificationInfo]:
        """Notification settings for the message."""
        return self.channel_data.notification if self.channel_data else None

    @property
    def tenant(self) -> Any:
        """Information about the tenant in which the message was sent."""
        return self.channel_data.tenant if self.channel_data else None

    def is_streaming(self) -> bool:
        """Check if this is a streaming activity."""
        return bool(self.entities and any(e.type == "streaminfo" for e in self.entities or []))
