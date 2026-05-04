"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from collections import deque
from typing import Awaitable, Callable, Optional, Union

from httpx import HTTPStatusError
from microsoft_teams.api import (
    ApiClient,
    ChannelData,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
    TypingActivityInput,
)
from microsoft_teams.common import EventEmitter

from .plugins.streamer import StreamCancelledError, StreamerEvent, StreamerProtocol
from .utils import RetryOptions, retry

logger = logging.getLogger(__name__)


class HttpStream(StreamerProtocol):
    """
    HTTP-based streaming implementation for Microsoft Teams activities.

    Flow:
    1. emit() adds activities to a queue
    2. _flush() drains the entire queue under a lock.
    3. Informative typing updates are sent immediately if no message started.
    4. Message text are combined into a typing chunk.
    5. Another flush is scheduled if more items remain.
    6. close() waits for queue to empty, then sends final message with stream_type='stream_final'

    The timeout cancellation ensures only one flush operation is scheduled at a time.
    The delays between flushes is to ensure we dont hit API rate limits with Microsoft Teams.
    """

    def __init__(self, client: ApiClient, ref: ConversationReference):
        """
        Initialize a new HttpStream instance.

        Args:
            client (ApiClient): The API client used to send activities to Microsoft Teams.
            ref (ConversationReference): Reference to the Teams conversation.
        """
        super().__init__()
        self._client = client
        self._ref = ref
        self._events = EventEmitter[StreamerEvent]()

        self._result: Optional[SentActivity] = None
        self._lock = asyncio.Lock()
        self._timeout: Optional[asyncio.TimerHandle] = None
        self._pending: Optional[asyncio.Task[None]] = None
        self._total_wait_timeout: float = 30.0
        self._state_changed = asyncio.Event()

        self._canceled = False
        self._reset_state()

    def _reset_state(self) -> None:
        """Reset the stream state to initial values."""
        self._index = 1
        self._id: Optional[str] = None
        self._text: str = ""
        self._channel_data: ChannelData = ChannelData()
        self._final_activity: Optional[MessageActivityInput] = None
        self._queue: deque[Union[MessageActivityInput, TypingActivityInput, str]] = deque()

    @property
    def canceled(self) -> bool:
        """
        Whether the stream has been canceled.
        For example when the user pressed the Stop button or the 2-minute timeout has exceeded.
        """
        return self._canceled

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

        if self._canceled:
            raise StreamCancelledError("Stream has been cancelled.")

        if isinstance(activity, str):
            activity = MessageActivityInput(text=activity, type="message")
        self._queue.append(activity)

        if not self._pending and not self._timeout:
            # Schedule a flush immediately when no timeout is set (first emit)
            self._pending = asyncio.create_task(self._flush())

    def update(self, text: str) -> None:
        """
        Send status updates before emitting (ex. "Thinking...").

        Args:
            text: The status text to send.
        """
        self.emit(TypingActivityInput().with_text(text).with_channel_data(ChannelData(stream_type="informative")))

    async def _wait_for_id_and_queue(self):
        """Wait until _id is set, the queue is empty, and no flush is in progress, with a total timeout."""

        async def _poll():
            while (self._queue or not self._id or self._lock.locked()) and not self._canceled:
                await self._state_changed.wait()
                self._state_changed.clear()

        try:
            await asyncio.wait_for(_poll(), timeout=self._total_wait_timeout)
            return True
        except asyncio.TimeoutError:
            return False

    async def close(self) -> Optional[SentActivity]:
        # wait for lock to be free
        if self._result is not None:
            logger.debug("stream already closed with result")
            return self._result

        if self._canceled:
            logger.debug("stream was cancelled, nothing to close")
            return None

        if self._index == 1 and not self._queue and not self._lock.locked():
            logger.debug("stream has no content to send, returning None")
            return None

        # Wait until _id is set and queue is empty
        result = await self._wait_for_id_and_queue()
        if not result:
            logger.warning(
                "Timeout while waiting for _id to be set, queue to be empty, and flush to complete, cannot close stream"
            )
            return None

        has_content = (
            self._text != ""
            or (self._final_activity and self._final_activity.attachments)
            or (self._final_activity and self._final_activity.suggested_actions)
        )
        if not has_content:
            logger.warning("no text, attachments, or suggested actions to send, cannot close stream")
            return None

        # Build final message from the last emitted MessageActivityInput (last wins)
        assert self._id is not None, "ID should be set by this point"
        activity = self._final_activity or MessageActivityInput()
        activity.with_text(self._text).with_id(self._id).with_channel_data(self._channel_data).add_stream_final()

        res = await retry(lambda: self._send(activity), options=RetryOptions())

        # Emit close event
        self._events.emit("close", res)

        # Reset state
        self._reset_state()
        self._result = res
        logger.debug("stream closed with result: %s", res)

        return res

    async def _flush(self) -> None:
        """
        Flush the current activity queue.
        """
        # If there are no items in the queue, nothing to flush
        if self._lock.locked():
            return

        await self._lock.acquire()

        try:
            if not self._queue:
                return
            if self._timeout is not None:
                self._timeout.cancel()
                self._timeout = None

            informative_updates: list[TypingActivityInput] = []
            start_length = len(self._queue)

            while self._queue:
                activity = self._queue.popleft()

                if isinstance(activity, MessageActivityInput):
                    self._text += activity.text or ""
                    self._final_activity = activity
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

            if start_length == 0:
                logger.debug("No activities to flush")
                return

            # Send informative updates immediately
            for typing_update in informative_updates:
                await self._send_activity(typing_update)

            # Send the combined text chunk
            if self._text:
                to_send = TypingActivityInput(text=self._text)
                await self._send_activity(to_send)

            # If more queued, schedule another flush
            if self._queue and not self._timeout:
                self._timeout = asyncio.get_running_loop().call_later(0.5, lambda: asyncio.create_task(self._flush()))

        finally:
            # Reset flushing flag so future emits can trigger another flush
            self._pending = None
            self._lock.release()
            self._state_changed.set()

    async def _send_activity(self, to_send: TypingActivityInput):
        """
        Send an activity to the Teams conversation with the ID.

        Args:
            activity: The activity to send.
        """
        if self._id:
            to_send = to_send.with_id(self._id)
        to_send = to_send.add_stream_update(self._index)

        res = await retry(
            lambda: self._send(to_send),
            options=RetryOptions(max_delay=4.0, jitter_type="none", max_attempts=8),
        )
        self._events.emit("chunk", res)
        self._index += 1
        if self._id is None:
            self._id = res.id
            self._state_changed.set()  # Notify that _id has been set

    async def _send(self, to_send: Union[TypingActivityInput, MessageActivityInput]) -> SentActivity:
        """
        Send or update an activity to the Teams conversation.

        Args:
            activity: The activity to send.
        """
        if self._canceled:
            logger.warning("Teams channel stopped the stream.")
            raise StreamCancelledError("Teams channel stopped the stream.")

        to_send.from_ = self._ref.bot
        to_send.conversation = self._ref.conversation

        try:
            if to_send.id and not any(e.type == "streaminfo" for e in (to_send.entities or [])):
                res = await self._client.conversations.activities(self._ref.conversation.id).update(to_send.id, to_send)
            else:
                res = await self._client.conversations.activities(self._ref.conversation.id).create(to_send)

            return SentActivity.merge(to_send, res)
        except HTTPStatusError as e:
            if e.response.status_code == 403:
                self._canceled = True
                logger.warning("Teams channel stopped the stream.")
                raise StreamCancelledError("Teams channel stopped the stream.") from e
            raise
