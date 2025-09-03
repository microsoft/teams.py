"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Awaitable, Callable, Literal, Optional, Protocol, Union

from microsoft.teams.api import MessageActivityInput, SentActivity, TypingActivityInput

StreamerEvent = Literal["chunk", "close"]


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

    def on_chunk(self, handler: Callable[[SentActivity], Awaitable[None]]) -> None:
        """
        Register a handler for chunk events.

        Args:
            handler: Async function that will be called for each chunk activity
        """
        ...

    def on_close(self, handler: Callable[[SentActivity], Awaitable[None]]) -> None:
        """
        Register a handler for close events.

        Args:
            handler: Async function that will be called when the stream closes
        """
        ...

    def emit(self, activity: Union[MessageActivityInput, TypingActivityInput, str]) -> None:
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
