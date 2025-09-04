"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from collections import deque
from logging import Logger
from typing import Awaitable, Callable, List, Optional, Union

from microsoft.teams.api import (
    ApiClient,
    Attachment,
    ChannelData,
    ConversationReference,
    Entity,
    MessageActivityInput,
    SentActivity,
    TypingActivityInput,
)
from microsoft.teams.common import ConsoleLogger, EventEmitter

from .plugins.streamer import StreamerEvent, StreamerProtocol
from .utils import RetryOptions, Timeout, retry


class HttpStream(StreamerProtocol):
    """
    HTTP-based streaming implementation for Microsoft Teams activities.

    Flow:
    1. emit() adds activities to a queue and cancels any pending flush timeout
    2. emit() schedules _flush() to run after 0.5 seconds via Timeout
    3. If another emit() happens before flush executes, the timeout is cancelled and rescheduled
    4. _flush() starts by cancelling any pending timeout, then processes up to 10 queued activities under a lock
    5. _flush() combines text from MessageActivity and sends it as a Typing activity with streamType='streaming'
    6. _flush() schedules another flush if more items remain in queue
    7. close() waits for queue to empty, then sends final message with stream_type='stream_final'

    The timeout cancellation ensures only one flush operation is scheduled at a time.
    The delays between flushes is to ensure we dont hit API rate limits with Microsoft Teams.
    """

    def __init__(self, client: ApiClient, ref: ConversationReference, logger: Optional[Logger] = None):
        """
        Initialize a new HttpStream instance.

        Args:
            client (ApiClient): The API client used to send activities to Microsoft Teams.
            ref (ConversationReference): Reference to the Teams conversation.
            logger (Optional[Logger]): Custom logger instance for debugging and monitoring..
        """
        super().__init__()
        self._client = client
        self._ref = ref
        self._logger = (
            logger.getChild("@teams/http-stream") if logger else ConsoleLogger().create_logger("@teams/http-stream")
        )
        self._events = EventEmitter[StreamerEvent]()

        self._result: Optional[SentActivity] = None
        self._lock = asyncio.Lock()
        self._timeout: Optional[Timeout] = None
        self._id_set_event = asyncio.Event()
        self._queue_empty_event = asyncio.Event()

        self._reset_state()

    def _reset_state(self) -> None:
        """Reset the stream state to initial values."""
        self._index = 1
        self._id: Optional[str] = None
        self._text: str = ""
        self._attachments: List[Attachment] = []
        self._channel_data: ChannelData = ChannelData()
        self._entities: List[Entity] = []
        self._queue: deque[Union[MessageActivityInput, TypingActivityInput, str]] = deque()

    @property
    def closed(self) -> bool:
        """Whether the final stream message has been sent."""
        return self._result is not None

    @property
    def count(self) -> int:
        """The total number of chunks queued to be sent."""
        return len(self._queue)

    @property
    def sequence(self) -> int:
        """The sequence number, representing the number of stream activities sent."""
        return self._index

    def on_chunk(self, handler: Callable[[SentActivity], Awaitable[None]]):
        self._events.on("chunk", handler)

    def on_close(self, handler: Callable[[SentActivity], Awaitable[None]]):
        self._events.once("close", handler)

    def emit(self, activity: Union[MessageActivityInput, TypingActivityInput, str]) -> None:
        """
        Emit a new activity to the stream.

        Args:
            activity: The activity to emit.
        """
        if self._timeout is not None:
            self._timeout.cancel()
            self._timeout = None

        if isinstance(activity, str):
            activity = MessageActivityInput(text=activity, type="message")
        self._queue.append(activity)

        # Clear the queue empty event since we just added an item
        self._queue_empty_event.clear()

        self._timeout = Timeout(0.5, self._flush)

    def update(self, text: str) -> None:
        """
        Send status updates before emitting (ex. "Thinking...").

        Args:
            text: The status text to send.
        """
        self.emit(TypingActivityInput().with_text(text).with_channel_data(ChannelData(stream_type="informative")))

    async def close(self) -> Optional[SentActivity]:
        # wait for lock to be free
        if self._result is not None:
            self._logger.debug("stream already closed with result")
            return self._result

        if self._index == 1 and not self._queue and not self._lock.locked():
            self._logger.debug("stream has no content to send, returning None")
            return None

        # Wait until _id is set and queue is empty
        if not self._id:
            self._logger.debug("waiting for ID to be set")
            await self._id_set_event.wait()

        while self._queue:
            self._logger.debug("waiting for queue to be empty...")
            await self._queue_empty_event.wait()

        if self._text == "" and self._attachments == []:
            self._logger.warning("no text or attachments to send, cannot close stream")
            return None

        # Build final message
        assert self._id is not None, "ID should be set by this point"
        activity = MessageActivityInput(text=self._text).with_id(self._id).with_channel_data(self._channel_data)
        activity.add_attachments(*self._attachments).add_entities(*self._entities).add_stream_final()

        res = await retry(lambda: self._send(activity), options=RetryOptions(logger=self._logger))

        # Emit close event
        self._events.emit("close", res)

        # Reset state
        self._reset_state()
        self._result = res
        self._logger.debug("stream closed with result: %s", res)

        return res

    async def _flush(self) -> None:
        """
        Flush the current activity queue.
        """
        # If there are no items in the queue, nothing to flush
        async with self._lock:
            if not self._queue:
                return

            if self._timeout is not None:
                self._timeout.cancel()
                self._timeout = None

            i = 0
            informative_updates: List[TypingActivityInput] = []

            while i < 10 and self._queue:
                activity = self._queue.popleft()

                if isinstance(activity, MessageActivityInput):
                    self._text += activity.text or ""
                    self._attachments.extend(activity.attachments or [])
                    self._entities.extend(activity.entities or [])
                if isinstance(activity, (MessageActivityInput, TypingActivityInput)) and activity.channel_data:
                    merged = {**self._channel_data.model_dump(), **activity.channel_data.model_dump()}
                    self._channel_data = ChannelData(**merged)
                if (
                    isinstance(activity, TypingActivityInput)
                    and getattr(activity.channel_data, "stream_type", None) == "informative"
                    and self._text == ""
                ):
                    # If `_text` is not empty then it's possible that streaming has started.
                    # And so informative updates cannot be sent.
                    informative_updates.append(activity)

                i += 1

            if i == 0:
                self._logger.debug("No activities to flush")
                return

            # Send informative updates immediately
            for typing_update in informative_updates:
                await self._send_activity(typing_update)

            # Send the combined text chunk
            if self._text:
                to_send = TypingActivityInput(text=self._text)
                await self._send_activity(to_send)

            # Signal if queue is now empty
            if not self._queue:
                self._queue_empty_event.set()

            # If more queued, schedule another flush
            if self._queue and not self._timeout:
                self._timeout = Timeout(0.5, self._flush)

    async def _send_activity(self, to_send: TypingActivityInput):
        """
        Send an activity to the Teams conversation with the ID.

        Args:
            activity: The activity to send.
        """
        if self._id:
            to_send = to_send.with_id(self._id)
        to_send = to_send.add_stream_update(self._index)

        res = await retry(lambda: self._send(to_send), options=RetryOptions(logger=self._logger))
        self._events.emit("chunk", res)
        self._index += 1
        if self._id is None:
            self._id = res.id
            # Signal that ID has been set
            self._id_set_event.set()

    async def _send(self, to_send: Union[TypingActivityInput, MessageActivityInput]) -> SentActivity:
        """
        Send or update an activity to the Teams conversation.

        Args:
            activity: The activity to send.
        """
        to_send.from_ = self._ref.bot
        to_send.conversation = self._ref.conversation

        if to_send.id and not any(e.type == "streaminfo" for e in (to_send.entities or [])):
            res = await self._client.conversations.activities(self._ref.conversation.id).update(to_send.id, to_send)
        else:
            res = await self._client.conversations.activities(self._ref.conversation.id).create(to_send)

        return SentActivity.merge(to_send, res)
