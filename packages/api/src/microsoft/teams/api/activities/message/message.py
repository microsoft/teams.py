"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Any, List, Literal, Optional, Self

from ...models import (
    Account,
    ActivityBase,
    Attachment,
    AttachmentLayout,
    ChannelData,
    DeliveryMode,
    Importance,
    InputHint,
    MentionEntity,
    StreamInfoEntity,
    SuggestedActions,
    TextFormat,
)
from ..utils import StripMentionsTextOptions, strip_mentions_text


class MessageActivity(ActivityBase):
    """Represents a message activity in Microsoft Teams."""

    type: Literal["message"] = "message"  # pyright: ignore [reportIncompatibleVariableOverride]

    text: str
    """The text content of the message."""

    speak: Optional[str] = None
    """The text to speak."""

    input_hint: Optional[InputHint] = None
    """
    Indicates whether your bot is accepting, expecting, or ignoring user input
    after the message is delivered to the client.
    """

    summary: Optional[str] = None
    """The text to display if the channel cannot render cards."""

    text_format: Optional[TextFormat] = None
    """Format of text fields. Default: markdown."""

    attachment_layout: Optional[AttachmentLayout] = None
    """The layout hint for multiple attachments. Default: list."""

    attachments: Optional[List[Attachment]] = None
    """Attachments"""

    suggested_actions: Optional[SuggestedActions] = None
    """The suggested actions for the activity."""

    importance: Optional[Importance] = None
    """The importance of the activity."""

    delivery_mode: Optional[DeliveryMode] = None
    """A delivery hint to signal to the recipient alternate delivery paths for the activity."""

    expiration: Optional[datetime] = None
    """
    The time at which the activity should be considered to be "expired"
    and should not be presented to the recipient.
    """

    value: Optional[Any] = None
    """A value that is associated with the activity."""

    # Utility methods

    def add_text(self, text: str) -> Self:
        """
        Append text to the message.

        Args:
            text: Text to append

        Returns:
            Self for method chaining
        """
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

    def add_card(self, content_type: str, content: Any) -> Self:
        """
        Add a card attachment to the message.

        Args:
            content_type: The content type of the card
            content: The card content

        Returns:
            Self for method chaining
        """
        card_attachment = Attachment(content_type=content_type, content=content)

        return self.add_attachments(card_attachment)

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
