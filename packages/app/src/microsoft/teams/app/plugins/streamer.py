"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional, Protocol, Union

from microsoft.teams.api.activities.message import MessageActivityInput
from microsoft.teams.api.activities.typing import TypingActivityInput
from microsoft.teams.api.models.resource import Resource
from microsoft.teams.common.events.event_emitter import EventEmitter

# Define the event names that streamers should support
IStreamerEvents = Literal["chunk", "close"]


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

    @property
    def events(self) -> EventEmitter[IStreamerEvents]:
        """
        Provides access to event listener registration for stream events,
        but does not allow emitting them directly.
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

    async def close(self) -> Optional[Resource]:
        """
        Close the stream.
        """
        ...
