"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, Self

from ..models import ActivityBase, ActivityInputBase, ChannelData, CustomBaseModel, StreamInfoEntity


class _TypingBase(CustomBaseModel):
    """Base class containing shared typing activity fields (all Optional except type)."""

    type: Literal["typing"] = "typing"

    text: Optional[str] = None
    """
    The text content of the message.
    """


class TypingActivity(_TypingBase, ActivityBase):
    """Output model for received typing activities with required fields and read-only properties."""


class TypingActivityInput(_TypingBase, ActivityInputBase):
    """Input model for creating typing activities with builder methods."""

    def with_text(self, value: str) -> Self:
        """Set the text content of the message."""
        self.text = value
        return self

    def add_text(self, text: str) -> Self:
        """Append text."""
        if self.text is None:
            self.text = ""
        self.text += text
        return self

    def add_stream_update(self, sequence: int = 1) -> Self:
        """Add stream informative update."""
        if self.channel_data is None:
            self.channel_data = ChannelData()

        self.channel_data.stream_id = self.id
        self.channel_data.stream_type = "streaming"
        self.channel_data.stream_sequence = sequence

        return self.add_entity(StreamInfoEntity(stream_id=self.id, stream_type="streaming", stream_sequence=sequence))
