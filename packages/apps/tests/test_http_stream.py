"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from microsoft_teams.api import (
    Account,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    SentActivity,
    TypingActivityInput,
)
from microsoft_teams.apps import HttpStream


class TestHttpStream:
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_api_client(self):
        client = MagicMock(spec=ApiClient)

        mock_activities = MagicMock()
        mock_conversations = MagicMock()
        mock_conversations.activities.return_value = mock_activities
        client.conversations = mock_conversations

        client.send_call_count = 0
        client.sent_activities = []

        async def mock_send(activity):
            client.send_call_count += 1
            client.sent_activities.append(activity)
            return SentActivity(id=f"activity-{client.send_call_count}", activity_params=activity)

        client.conversations.activities().create = mock_send

        return client

    @pytest.fixture
    def conversation_reference(self):
        return ConversationReference(
            service_url="https://smba.trafficmanager.net/teams/",
            bot=Account(id="test-bot", name="Test Bot"),
            conversation=ConversationAccount(id="test-conversation", conversation_type="personal"),
            activity_id="test-activity",
            channel_id="msteams",
        )

    @pytest.fixture
    def http_stream(self, mock_api_client, conversation_reference, mock_logger):
        return HttpStream(mock_api_client, conversation_reference, mock_logger)

    @pytest.fixture
    def patch_loop_call_later(self):
        """Patch the event loop call_later to store scheduled callbacks."""
        scheduled = []

        def _patch(loop):
            def mock_call_later(delay, callback, *args):
                scheduled.append((callback, args))
                return MagicMock()  # fake TimerHandle

            return patch.object(loop, "call_later", side_effect=mock_call_later), scheduled

        return _patch

    async def _run_scheduled_flushes(self, scheduled):
        """Helper to run all scheduled flush callbacks asynchronously."""
        while scheduled:
            callback, args = scheduled.pop(0)
            callback(*args)
            await asyncio.sleep(0)

    @pytest.mark.asyncio
    async def test_stream_multiple_emits_with_timer(self, http_stream, patch_loop_call_later):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            for i in range(12):
                http_stream.emit(f"Message {i + 1}")

            await asyncio.sleep(0)
            assert http_stream._client.send_call_count == 1

            await self._run_scheduled_flushes(scheduled)
            assert http_stream._client.send_call_count == 2

    @pytest.mark.asyncio
    async def test_stream_error_handled_gracefully(
        self, mock_api_client, conversation_reference, mock_logger, patch_loop_call_later
    ):
        call_count = 0
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_with_timeout(activity):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    raise TimeoutError("Operation timed out")
                return SentActivity(id=f"success-after-timeout-{call_count}", activity_params=activity)

            mock_api_client.conversations.activities().create = mock_send_with_timeout
            stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

            stream.emit("Test message with timeout")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)
            assert call_count == 2

            result = await stream.close()
            assert result is not None

    @pytest.mark.asyncio
    async def test_stream_all_timeouts_fail_handled_gracefully(
        self, mock_api_client, conversation_reference, mock_logger, patch_loop_call_later
    ):
        call_count = 0
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:

            async def mock_send_all_timeout(activity):
                nonlocal call_count
                call_count += 1
                raise TimeoutError("All operations timed out")

            mock_api_client.conversations.activities().create = mock_send_all_timeout
            stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

            stream.emit("Test message with all timeouts")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)
            assert call_count == 8
            await stream.close()

    @pytest.mark.asyncio
    async def test_stream_update_status_sends_typing_activity(
        self, mock_api_client, conversation_reference, mock_logger, patch_loop_call_later
    ):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, mock_logger)
            stream.update("Thinking...")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert len(mock_api_client.sent_activities) > 0
            activity = mock_api_client.sent_activities[0]
            assert isinstance(activity, TypingActivityInput)
            assert activity.text == "Thinking..."
            assert activity.channel_data is not None
            assert activity.channel_data.stream_type == "informative"
            assert stream.sequence >= 2

    @pytest.mark.asyncio
    async def test_stream_sequence_of_update_and_emit(
        self, mock_api_client, conversation_reference, mock_logger, patch_loop_call_later
    ):
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)
        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, mock_logger)
            stream.update("Preparing response...")
            stream.emit("Final response message")
            await asyncio.sleep(0)
            await self._run_scheduled_flushes(scheduled)

            assert len(mock_api_client.sent_activities) >= 2
            typing_activity = mock_api_client.sent_activities[0]
            message_activity = mock_api_client.sent_activities[1]

            assert isinstance(typing_activity, TypingActivityInput)
            assert typing_activity.text == "Preparing response..."
            assert message_activity.text == "Final response message"
            assert stream.sequence >= 3

    @pytest.mark.asyncio
    async def test_stream_concurrent_emits_do_not_flush_simultaneously(
        self, mock_api_client, conversation_reference, mock_logger, patch_loop_call_later
    ):
        concurrent_entries = 0
        max_concurrent_entries = 0
        lock = asyncio.Lock()
        loop = asyncio.get_running_loop()
        patcher, scheduled = patch_loop_call_later(loop)

        async def mock_send(activity):
            nonlocal concurrent_entries, max_concurrent_entries
            async with lock:
                concurrent_entries += 1
                max_concurrent_entries = max(max_concurrent_entries, concurrent_entries)
            await asyncio.sleep(0)
            async with lock:
                concurrent_entries -= 1
            return activity

        mock_api_client.conversations.activities().create = mock_send

        with patcher:
            stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

            async def emit_task():
                stream.emit("Concurrent message")

            tasks = [asyncio.create_task(emit_task()) for _ in range(10)]
            await asyncio.gather(*tasks)
            await self._run_scheduled_flushes(scheduled)

            assert max_concurrent_entries == 1
