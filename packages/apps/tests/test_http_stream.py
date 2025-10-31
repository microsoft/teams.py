"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
from unittest.mock import MagicMock

import pytest
from microsoft.teams.api import (
    Account,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    SentActivity,
    TypingActivityInput,
)
from microsoft.teams.apps import HttpStream


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
            await asyncio.sleep(0.05)  # Simulate network delay
            return SentActivity(id=f"test-id-{client.send_call_count}", activity_params=activity)

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

    @pytest.mark.asyncio
    async def test_stream_emit_message_flushes_immediately(self, mock_api_client, conversation_reference, mock_logger):
        """Test that messages are flushed immediately."""

        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)
        stream.emit("Test message")
        await asyncio.sleep(0.07)  # Wait for the flush task to complete
        assert mock_api_client.send_call_count == 1

    @pytest.mark.asyncio
    async def test_stream_multiple_emits_timer_check(self, mock_api_client, conversation_reference, mock_logger):
        """Test that multiple emits reset the timer."""

        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        stream.emit("First message")
        stream.emit("Second message")
        stream.emit("Third message")
        stream.emit("Fourth message")
        stream.emit("Fifth message")
        stream.emit("Sixth message")
        stream.emit("Seventh message")
        stream.emit("Eighth message")
        stream.emit("Ninth message")
        stream.emit("Tenth message")
        stream.emit("Eleventh message")
        stream.emit("Twelfth message")

        await asyncio.sleep(0.07)  # Wait for the flush task to complete
        assert mock_api_client.send_call_count == 1  # First message should trigger flush immediately

        stream.emit("Thirteenth message")
        await asyncio.sleep(0.3)  # Less than 500ms from first flush
        assert mock_api_client.send_call_count == 1, "No new flush should have occurred yet"

        await asyncio.sleep(0.3)  # Now exceed 500ms from last emit
        assert mock_api_client.send_call_count == 2, "Second flush should have occurred"

    @pytest.mark.asyncio
    async def test_stream_error_handled_gracefully(self, mock_api_client, conversation_reference, mock_logger):
        """Test that send timeouts are handled gracefully with retries."""
        call_count = 0

        async def mock_send_with_timeout(activity):
            nonlocal call_count
            call_count += 1
            if call_count == 1:  # Fail first attempt
                raise TimeoutError("Operation timed out")

            # Succeed on second attempt
            await asyncio.sleep(0.05)  # Simulate delay
            return SentActivity(id=f"success-after-timeout-{call_count}", activity_params=activity)

        mock_api_client.conversations.activities().create = mock_send_with_timeout

        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        stream.emit("Test message with timeout")
        await asyncio.sleep(0.6)  # Wait for flush and 1 retry to complete

        result = await stream.close()

        assert call_count > 1, "Should have retried after timeout"
        assert result is not None

    @pytest.mark.asyncio
    async def test_stream_all_timeouts_fail_handled_gracefully(
        self, mock_api_client, conversation_reference, mock_logger
    ):
        """Test that when all timeouts fail, it's handled gracefully."""
        call_count = 0

        async def mock_send_all_timeout(activity):
            nonlocal call_count
            call_count += 1
            raise TimeoutError("All operations timed out")

        mock_api_client.conversations.activities().create = mock_send_all_timeout

        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        stream.emit("Test message with all timeouts")
        await asyncio.sleep(5.0)  # Wait for flush and all retries to complete

        await stream.close()
        assert call_count > 1, "Should have retried after timeout"

    @pytest.mark.asyncio
    async def test_stream_update_status_sends_typing_activity(
        self, mock_api_client, conversation_reference, mock_logger
    ):
        """Test that update sends typing activities."""
        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        stream.update("Thinking...")
        await asyncio.sleep(0.07)  # Wait for the flush task to complete

        assert stream.count > 0 or len(mock_api_client.sent_activities) > 0, "Should have processed the update"
        assert stream.sequence >= 2, "Should increment sequence after sending"

        assert len(mock_api_client.sent_activities) > 0, "Should have sent at least one activity"
        sent_activity = mock_api_client.sent_activities[0]
        assert isinstance(sent_activity, TypingActivityInput)
        assert sent_activity.text == "Thinking..."
        assert sent_activity.channel_data is not None
        assert sent_activity.channel_data.stream_type == "informative"

    @pytest.mark.asyncio
    async def test_stream_sequence_of_update_and_emit(self, mock_api_client, conversation_reference, mock_logger):
        """Test a sequence of update() followed by emit(), ensuring correct ordering and flush behavior."""

        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        stream.update("Preparing response...")
        stream.emit("Final response message")

        await asyncio.sleep(0.5)  # Wait for the flush task to complete

        assert len(mock_api_client.sent_activities) >= 2, "Should have sent typing activity and message"

        typing_activity = mock_api_client.sent_activities[0]
        message_activity = mock_api_client.sent_activities[1]

        # First should be typing activity from update()
        assert isinstance(typing_activity, TypingActivityInput)
        assert typing_activity.text == "Preparing response..."

        # Second should be a normal message from emit()
        assert message_activity.text == "Final response message"

        # Sequence numbers should have increased
        assert stream.sequence >= 3, "Sequence should increment for both update and emit"

    @pytest.mark.asyncio
    async def test_stream_concurrent_emits_do_not_flush_simultaneously(
        self, mock_api_client, conversation_reference, mock_logger
    ):
        """
        Test that multiple concurrent emits do not allow simultaneous flush execution.
        """
        concurrent_entries = 0
        max_concurrent_entries = 0
        lock = asyncio.Lock()

        async def mock_send(activity):
            nonlocal concurrent_entries, max_concurrent_entries
            async with lock:
                concurrent_entries += 1
                max_concurrent_entries = max(max_concurrent_entries, concurrent_entries)
            await asyncio.sleep(0.05)  # simulate delay in sending
            async with lock:
                concurrent_entries -= 1
            return activity

        mock_api_client.conversations.activities().create = mock_send

        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        # Schedule multiple emits concurrently
        async def emit_task():
            stream.emit("Concurrent message")

        tasks = [asyncio.create_task(emit_task()) for _ in range(10)]
        await asyncio.gather(*tasks)

        # Wait for flushes to complete
        await asyncio.sleep(0.07)

        # Only one flush should have entered the critical section at a time
        assert max_concurrent_entries == 1, f"Flush entered concurrently {max_concurrent_entries} times, expected 1"
