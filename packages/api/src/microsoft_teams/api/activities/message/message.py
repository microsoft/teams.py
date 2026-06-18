"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, List, Literal, Optional, Self

from microsoft_teams.cards import AdaptiveCard
from microsoft_teams.common.experimental import experimental

from ...models import (
    Account,
    ActivityBase,
    ActivityInputBase,
    AdaptiveCardAttachment,
    Attachment,
    AttachmentLayout,
    ChannelData,
    CustomBaseModel,
    DeliveryMode,
    MentionEntity,
    QuotedReplyData,
    QuotedReplyEntity,
    StreamInfoEntity,
    SuggestedActions,
    TextFormat,
)
from ...models.channel_data import FeedbackLoop
from ...models.entity import (
    AIMessageEntity,
    Appearance,
    CitationAppearance,
    CitationEntity,
    Claim,
    Entity,
    Image,
    MessageEntity,
    TargetedMessageInfoEntity,
)
from ..utils import StripMentionsTextOptions, strip_mentions_text


class _MessageBase(CustomBaseModel):
    """Base class containing shared message activity fields (all Optional except type)."""

    type: Literal["message"] = "message"

    text: Optional[str] = None
    """The text content of the message."""

    summary: Optional[str] = None
    """The text to display if the channel cannot render cards."""

    text_format: Optional[TextFormat] = None
    """Format of text fields. Default: markdown. Possible values: 'markdown', 'plain', 'xml', 'extendedmarkdown'."""

    attachment_layout: Optional[AttachmentLayout] = None
    """The layout hint for multiple attachments. Default: list."""

    attachments: Optional[List[Attachment]] = None
    """Attachments"""

    suggested_actions: Optional[SuggestedActions] = None
    """The suggested actions for the activity."""

    delivery_mode: Optional[DeliveryMode] = None
    """A delivery hint to signal to the recipient alternate delivery paths for the activity."""

    value: Optional[Any] = None
    """A value that is associated with the activity."""


class MessageActivity(_MessageBase, ActivityBase):
    """Output model for received message activities with required fields and read-only properties."""

    text: str = ""  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """The text content of the message."""

    def get_quoted_messages(self) -> list[QuotedReplyEntity]:
        """
        Get all quoted reply entities from this message.

        Returns:
            List of quoted reply entities, empty if none
        """
        return [e for e in (self.entities or []) if isinstance(e, QuotedReplyEntity)]

    def is_recipient_mentioned(self) -> bool:
        """
        Check if the recipient account is mentioned in the message.

        Returns:
            True if the recipient is mentioned
        """
        if not self.entities or not self.recipient:
            return False

        for entity in self.entities or []:
            if isinstance(entity, MentionEntity):
                mentioned_id = entity.mentioned.id
                if mentioned_id == self.recipient.id:
                    return True
        return False

    def get_account_mention(self, account_id: str) -> Optional[MentionEntity]:
        """
        Get a mention entity by account ID.

        Args:
            account_id: The account ID to search for

        Returns:
            The mention entity if found, None otherwise
        """
        if not self.entities:
            return None

        for entity in self.entities or []:
            if isinstance(entity, MentionEntity):
                if entity.mentioned.id == account_id:
                    return entity
        return None

    def strip_mentions_text(self, options: Optional[StripMentionsTextOptions] = None) -> Self:
        """
        Remove "<at>...</at>" text from the message.

        Args:
            options: Options for stripping mentions

        Returns:
            Self for method chaining
        """

        stripped_text = strip_mentions_text(self, options)
        if stripped_text is not None:
            self.text = stripped_text
        return self


class MessageActivityInput(_MessageBase, ActivityInputBase):
    """Input model for creating message activities with builder methods."""

    def with_text(self, text: str) -> Self:
        """
        Set the text content of the message.

        Args:
            text: Text to set

        Returns:
            Self for method chaining
        """
        self.text = text
        return self

    def with_summary(self, summary: str) -> Self:
        """
        Set the text to display if the channel cannot render cards.

        Args:
            summary: Summary text

        Returns:
            Self for method chaining
        """
        self.summary = summary
        return self

    def with_text_format(self, text_format: TextFormat) -> Self:
        """
        Set the format of text fields.

        Args:
            text_format: Text format (markdown, plain, xml, extendedmarkdown)

        Returns:
            Self for method chaining
        """
        self.text_format = text_format
        return self

    def with_attachment_layout(self, attachment_layout: AttachmentLayout) -> Self:
        """
        Set the layout hint for multiple attachments.

        Args:
            attachment_layout: Attachment layout (list, carousel)

        Returns:
            Self for method chaining
        """
        self.attachment_layout = attachment_layout
        return self

    def with_suggested_actions(self, suggested_actions: SuggestedActions) -> Self:
        """
        Set the suggested actions for the activity.

        Args:
            suggested_actions: Suggested actions

        Returns:
            Self for method chaining
        """
        self.suggested_actions = suggested_actions
        return self

    def with_delivery_mode(self, delivery_mode: DeliveryMode) -> Self:
        """
        Set the delivery mode for the activity.

        Args:
            delivery_mode: Delivery mode (normal, notification)

        Returns:
            Self for method chaining
        """
        self.delivery_mode = delivery_mode
        return self

    def add_text(self, text: str) -> Self:
        """
        Append text to the message.

        Args:
            text: Text to append

        Returns:
            Self for method chaining
        """
        if self.text is None:
            self.text = text
        else:
            self.text += text
        return self

    def add_attachments(self, *attachments: Attachment) -> Self:
        """
        Add attachments to the message.

        Args:
            *attachments: Attachments to add

        Returns:
            Self for method chaining
        """
        if not self.attachments:
            self.attachments = []
        self.attachments.extend(attachments)
        return self

    def add_mention(self, account: Account, text: Optional[str] = None, add_text: bool = True) -> Self:
        """
        Add a mention (@mention) to the message.

        Args:
            account: The account to mention
            text: Custom text for the mention (defaults to account.name)
            add_text: Whether to append the mention text to the message

        Returns:
            Self for method chaining
        """
        mention_text = text or account.name

        if add_text:
            self.add_text(f"<at>{mention_text}</at>")

        mention_entity = MentionEntity(mentioned=account, text=f"<at>{mention_text}</at>")

        return self.add_entity(mention_entity)

    def add_card(self, card: AdaptiveCard) -> Self:
        """
        Add a card attachment to the message.

        Args:
            card: The card attachment to add
            content: The card content

        Returns:
            Self for method chaining
        """
        card_attachment = AdaptiveCardAttachment(
            content=card,
        )
        attachment = Attachment(content_type=card_attachment.content_type, content=card)

        return self.add_attachments(attachment)

    def is_recipient_mentioned(self) -> bool:
        """
        Check if the recipient account is mentioned in the message.

        Returns:
            True if the recipient is mentioned
        """
        if not self.entities or not self.recipient:
            return False

        for entity in self.entities:
            if isinstance(entity, MentionEntity):
                mentioned_id = entity.mentioned.id
                if mentioned_id == self.recipient.id:
                    return True
        return False

    def get_account_mention(self, account_id: str) -> Optional[MentionEntity]:
        """
        Get a mention entity by account ID.

        Args:
            account_id: The account ID to search for

        Returns:
            The mention entity if found, None otherwise
        """
        if not self.entities:
            return None

        for entity in self.entities:
            if isinstance(entity, MentionEntity):
                if entity.mentioned.id == account_id:
                    return entity
        return None

    def add_stream_final(self) -> Self:
        """
        Add stream info, making this a final stream message.

        Returns:
            Self for method chaining
        """

        # Update channel data
        if not self.channel_data:
            self.channel_data = ChannelData()

        # Set stream properties on channel data
        if hasattr(self.channel_data, "stream_id"):
            self.channel_data.stream_id = self.id
        if hasattr(self.channel_data, "stream_type"):
            self.channel_data.stream_type = "final"

        # Add stream info entity
        stream_entity = StreamInfoEntity(type="streaminfo", stream_id=self.id, stream_type="final")

        return self.add_entity(stream_entity)

    def add_ai_generated(self) -> Self:
        """Add the 'Generated By AI' label."""
        message_entity = self._ensure_single_root_level_message_entity()
        ai_entity = AIMessageEntity(**message_entity.model_dump())
        if ai_entity.additional_type and "AIGeneratedContent" in ai_entity.additional_type:
            return self

        if not ai_entity.additional_type:
            ai_entity.additional_type = []

        ai_entity.additional_type.append("AIGeneratedContent")

        self._update_entity(message_entity, ai_entity)

        return self

    def add_citation(self, position: int, appearance: CitationAppearance) -> Self:
        """Add citations."""
        message_entity = self._ensure_single_root_level_message_entity()
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

    def _ensure_single_root_level_message_entity(self) -> MessageEntity:
        """
        Get or create the base message entity.
        There should only be one root level message entity.
        """
        message_entity = next(
            (
                e
                for e in (self.entities or [])
                if isinstance(e, MessageEntity) and e.type == "https://schema.org/Message" and e.at_type == "Message"
            ),
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

    def add_feedback(self, mode: Literal["default", "custom"] = "default") -> Self:
        """
        Enable message feedback.

        Args:
            mode: "default" shows Teams' built-in thumbs up/down UI.
                  "custom" triggers a message/fetchTask invoke so the bot
                  can return its own task module dialog.
        """
        if not self.channel_data:
            self.channel_data = ChannelData()
        self.channel_data.feedback_loop = FeedbackLoop(type=mode)
        self.channel_data.feedback_loop_enabled = None
        return self

    def prepend_quote(self, message_id: str) -> Self:
        """
        Prepend a quotedReply entity and placeholder before existing text.
        Used by reply()/quote() for quote-above-response.

        Args:
            message_id: The IC3 message ID of the message to quote

        Returns:
            Self for method chaining
        """
        if not self.entities:
            self.entities = []
        self.entities.append(QuotedReplyEntity(quoted_reply=QuotedReplyData(message_id=message_id)))
        placeholder = f'<quoted messageId="{message_id}"/>'
        has_text = bool((self.text or "").strip())
        self.text = f"{placeholder} {self.text}" if has_text else placeholder
        return self

    def add_quote(self, message_id: str, text: str | None = None) -> Self:
        """
        Add a quoted message reference and append a placeholder to text.
        Teams renders the quoted message as a preview bubble above the response text.
        If text is provided, it is appended to the quoted message placeholder.

        Args:
            message_id: The ID of the message to quote
            text: Optional text, appended to the quoted message placeholder

        Returns:
            Self for method chaining
        """
        if not self.entities:
            self.entities = []
        self.entities.append(QuotedReplyEntity(quoted_reply=QuotedReplyData(message_id=message_id)))
        self.add_text(f'<quoted messageId="{message_id}"/>')
        if text:
            self.add_text(f" {text}")
        return self

    @experimental("ExperimentalTeamsTargeted")
    def add_targeted_message_info(self, message_id: str) -> Self:
        """Add a targetedMessageInfo entity for prompt preview.

        If an entity with type ``"targetedMessageInfo"`` already exists,
        it is not added again (one prompt preview per message).

        When adding the entity, any ``quotedReply`` entities and matching
        ``<quoted messageId="..."/>`` placeholder text are removed to avoid
        collision with prompt preview.

        Args:
            message_id: The message ID of the targeted message.

        Returns:
            Self for method chaining
        """
        has_entity = any(isinstance(e, TargetedMessageInfoEntity) for e in (self.entities or []))

        # Always strip quotedReply artifacts to avoid collision with prompt preview,
        # if the developer already attached a targetedMessageInfo entity.
        if self.entities is not None:
            self.entities = [e for e in self.entities if getattr(e, "type", None) != "quotedReply"]
        if self.text is not None:
            self.text = self.text.replace(f'<quoted messageId="{message_id}"/>', "").strip()

        if not has_entity:
            self.add_entity(TargetedMessageInfoEntity(message_id=message_id))
        return self

    def with_recipient(self, value: Account, is_targeted: Optional[bool] = None) -> Self:
        """
        Set the recipient.

        Args:
            value: The recipient account
            is_targeted: If True, marks this as a targeted message visible only to this
                recipient. If False, explicitly clears targeting. If None (the default),
                the existing is_targeted value is left unchanged.

        Returns:
            Self for method chaining
        """
        return super().with_recipient(value, is_targeted)
