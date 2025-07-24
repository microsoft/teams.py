"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Dict, Literal, Optional, Self

from ..models import ActivityBase, ChannelData, CustomBaseModel, StreamInfoEntity


class TypingActivity(ActivityBase, CustomBaseModel):
    type: Literal["typing"] = "typing"  # pyright: ignore [reportIncompatibleVariableOverride]

    text: Optional[str] = None
    """
    The text content of the message.
    """

    def __init__(self, value: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(value={"type": "typing", **(value or {})})

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
