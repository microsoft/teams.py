"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from collections import deque
from logging import Logger
from typing import List, Optional, Union

from microsoft.teams.api import ConversationReference, Resource
from microsoft.teams.api.activities.message.message import MessageActivityInput
from microsoft.teams.api.activities.typing import TypingActivityInput
from microsoft.teams.api.clients.api_client import ApiClient
from microsoft.teams.api.models.attachment import Attachment
from microsoft.teams.api.models.channel_data import ChannelData
from microsoft.teams.api.models.entity import Entity
from microsoft.teams.app.utils.retry import RetryOptions, retry
from microsoft.teams.common.events.event_emitter import EventEmitter
from microsoft.teams.common.logging import ConsoleLogger

from .plugins.streamer import IStreamerEvents, StreamerProtocol


class HttpStream(StreamerProtocol):
    def __init__(self, client: ApiClient, ref: ConversationReference, logger: Optional[Logger] = None):
        self._client = client
        self._ref = ref
        self._logger = logger or ConsoleLogger().create_logger("@teams/http-stream")
        self._events = EventEmitter[IStreamerEvents]()

        self._index = 0
        self._id: Optional[str] = None
        self._text: str = ""
        self._attachments: List[Attachment] = []
        self._channel_data: ChannelData = ChannelData()
        self._entities: List[Entity] = []
        self._queue: deque[Union[MessageActivityInput, TypingActivityInput, str]] = deque()

        self._result: Optional[Resource] = None
        self._lock = asyncio.Lock()
        self._timeout: Optional[asyncio.Task[None]] = None
        self._id_set_event = asyncio.Event()
        self._queue_empty_event = asyncio.Event()

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

    @property
    def events(self) -> EventEmitter[IStreamerEvents]:
        """
        Provides access to event listener registration for stream events,
        but does not allow emitting them directly.
        """
        return self._events

    def emit(self, activity: Union[MessageActivityInput, TypingActivityInput, str]) -> None:
        if self._timeout is not None:
            self._timeout.cancel()
            self._timeout = None

        if isinstance(activity, str):
            activity = MessageActivityInput(text=activity, type="message")
        self._queue.append(activity)

        # Clear the queue empty event since we just added an item
        self._queue_empty_event.clear()

        self._timeout = asyncio.create_task(self._delayed_flush())

    def update(self, text: str) -> None:
        self.emit(TypingActivityInput().with_text(text).with_channel_data(ChannelData(stream_type="informative")))

    async def close(self) -> Optional[Resource]:
        if self._result is not None:
            self._logger.debug("stream already closed with result")
            return self._result

        if not self._index and not self._queue:
            self._logger.debug("no content")
            return None

        # Wait until _id is set and queue is empty
        while not self._id or self._queue:
            # Create tasks for the events we're waiting for
            tasks: List[asyncio.Task[bool]] = []
            if not self._id:
                tasks.append(asyncio.create_task(self._id_set_event.wait()))
            if self._queue:
                tasks.append(asyncio.create_task(self._queue_empty_event.wait()))

            if tasks:
                # Wait for at least one event to be set
                await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                # Cancel any remaining tasks
                for task in tasks:
                    task.cancel()

        # Build final message
        activity = MessageActivityInput(text=self._text).with_id(self._id).with_channel_data(self._channel_data)
        activity.add_attachments(*self._attachments).add_entities(*self._entities).add_stream_final()

        res = await retry(lambda: self._send_activity(activity), options=RetryOptions(logger=self._logger))

        # Emit close event
        self._events.emit("close", res)

        # Reset state
        self._index = 0
        self._id = None
        self._text = ""
        self._attachments = []
        self._entities = []
        self._channel_data = ChannelData()
        self._result = res
        self._logger.debug("stream closed with result: %s", res)

        return res

    async def _delayed_flush(self):
        await asyncio.sleep(0.2)
        await self._flush()

    async def _flush(self) -> None:
        # If there are no items in the queue, nothing to flush
        async with self._lock:
            if not self._queue:
                return

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
            to_send = TypingActivityInput(text=self._text)
            if self._id:
                to_send = to_send.with_id(self._id)
            to_send = to_send.add_stream_update(self._index)
            res = await retry(lambda: self._send_activity(to_send), options=RetryOptions(logger=self._logger))  # type: ignore

            self._events.emit("chunk", res)
            self._index += 1
            if self._id is None:
                self._id = res.id
                # Signal that ID has been set
                self._id_set_event.set()

            # Signal if queue is now empty
            if not self._queue:
                self._queue_empty_event.set()

            # If more queued, schedule another flush
            if self._queue:
                self._flush_task = asyncio.create_task(self._delayed_flush())

    async def _send_activity(self, to_send: Union[TypingActivityInput, MessageActivityInput]) -> Resource:
        to_send.from_ = self._ref.bot
        to_send.conversation = self._ref.conversation

        if to_send.id and not any(e.type == "streaminfo" for e in (to_send.entities or [])):
            return await self._client.conversations.activities(self._ref.conversation.id).update(to_send.id, to_send)
        else:
            return await self._client.conversations.activities(self._ref.conversation.id).create(to_send)
