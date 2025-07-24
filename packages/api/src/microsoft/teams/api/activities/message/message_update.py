"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Any, Literal, Optional, Self

from ...models import ActivityBase, ChannelData

MessageEventType = Literal["undeleteMessage", "editMessage"]


class MessageUpdateChannelData(ChannelData):
    """Channel data specific to message update activities."""

    event_type: MessageEventType  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """The type of event for message update."""


class MessageUpdateActivity(ActivityBase):
    """Represents a message update activity in Microsoft Teams."""

    type: Literal["messageUpdate"] = "messageUpdate"  # pyright: ignore [reportIncompatibleVariableOverride]

    text: str
    """The text content of the message."""

    speak: Optional[str] = None
    """The text to speak."""

    summary: Optional[str] = None
    """The text to display if the channel cannot render cards."""

    expiration: Optional[datetime] = None
    """
    The time at which the activity should be considered to be "expired"
    and should not be presented to the recipient.
    """

    value: Optional[Any] = None
    """A value that is associated with the activity."""

    channel_data: MessageUpdateChannelData  # pyright: ignore [reportGeneralTypeIssues, reportIncompatibleVariableOverride]
    """Channel-specific data for message update events."""

    def with_text(self, text: str) -> Self:
        """
        Set the text content of the message.

        Args:
            text: The text content to set

        Returns:
            Self for method chaining
        """
        self.text = text
        return self

    def with_speak(self, speak: str) -> Self:
        """
        Set the text to speak.

        Args:
            speak: The text to speak

        Returns:
            Self for method chaining
        """
        self.speak = speak
        return self

    def with_summary(self, summary: str) -> Self:
        """
        Set the summary text.

        Args:
            summary: The summary text to set

        Returns:
            Self for method chaining
        """
        self.summary = summary
        return self

    def with_expiration(self, expiration: datetime) -> Self:
        """
        Set the expiration time for the activity.

        Args:
            expiration: The expiration datetime to set

        Returns:
            Self for method chaining
        """
        self.expiration = expiration
        return self
