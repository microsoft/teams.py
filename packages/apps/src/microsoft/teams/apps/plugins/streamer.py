"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Optional, Protocol, Union

from microsoft.teams.api.activities import MessageActivity, SentActivity, TypingActivity


class StreamerProtocol(Protocol):
    """Component that can send streamed chunks of an activity."""

    @property
    def closed(self) -> bool:
        """Whether the final stream message has been sent."""
        ...

    @property
    def count(self) -> int:
        """The total number of chunks queued to be sent."""
        ...

    @property
    def sequence(self) -> int:
        """
        The sequence number, representing the number of stream activities sent.

        Several chunks can be aggregated into one stream activity
        due to differences in Api rate limits.
        """
        ...

    def emit(self, activity: Union[MessageActivity, TypingActivity, str]) -> None:
        """
        Emit an activity chunk.
        """
        ...

    def update(self, text: str) -> None:
        """
        Send status updates before emitting (ex. "Thinking...").

        Args:
            text: The status text to send.
        """
        ...

    async def close(self) -> Optional[SentActivity]:
        """
        Close the stream.
        """
        ...
