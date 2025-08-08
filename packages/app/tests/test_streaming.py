"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.api.activities.message.message import MessageActivityInput
from microsoft.teams.api.activities.typing import TypingActivityInput
from microsoft.teams.api.clients.api_client import ApiClient
from microsoft.teams.api.models import ConversationReference, Resource
from microsoft.teams.api.models.account import Account, ConversationAccount
from microsoft.teams.app.http_stream import HttpStream


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

        mock_activities.create = AsyncMock(return_value=Resource(id="mock-id"))
        mock_activities.update = AsyncMock(return_value=Resource(id="mock-id"))

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

    def test_initial_state(self, http_stream):
        assert not http_stream.closed
        assert http_stream.count == 0
        assert http_stream.sequence == 1
        assert http_stream._text == ""
        assert len(http_stream._attachments) == 0
        assert len(http_stream._entities) == 0

    @pytest.mark.asyncio
    async def test_emit_string(self, http_stream):
        http_stream.emit("Hello, world!")

        # Wait for the flush task to complete
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=1.0)

        assert http_stream.count == 0
        assert http_stream.sequence == 2

    @pytest.mark.asyncio
    async def test_emit_activity(self, http_stream, mock_api_client):
        activity = MessageActivityInput(text="Test message", type="message")

        http_stream.emit(activity)
        # Wait for the flush task to complete
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=0.3)

        assert http_stream.count == 0
        assert http_stream.sequence == 2

        mock_api_client.conversations.activities().create.assert_called_once()
        sent_activity = mock_api_client.conversations.activities().create.call_args[0][0]
        # Should have sent a TypingActivityInput (not Message)
        assert isinstance(sent_activity, TypingActivityInput)
        assert sent_activity.text == "Test message"
        assert http_stream._id == "mock-id"

    @pytest.mark.asyncio
    async def test_update_status(self, http_stream, mock_api_client):
        http_stream.update("Thinking...")
        # Wait for the flush task to complete
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=0.3)

        assert http_stream.count == 0
        assert http_stream.sequence == 2

        mock_api_client.conversations.activities().create.assert_called()
        first_call_args = mock_api_client.conversations.activities().create.call_args_list[0]
        sent_activity = first_call_args[0][0]
        assert isinstance(sent_activity, TypingActivityInput)
        assert sent_activity.text == "Thinking..."
        assert http_stream._id == "mock-id"

        second_call_args = mock_api_client.conversations.activities().create.call_args_list[1]
        sent_activity = second_call_args[0][0]
        # Should have sent a TypingActivityInput (not Message)
        assert isinstance(sent_activity, TypingActivityInput)
        assert sent_activity.text == ""

    @pytest.mark.asyncio
    async def test_multiple_emits(self, http_stream, mock_api_client):
        http_stream.emit("Hello")
        http_stream.emit(" ")
        http_stream.emit("world!")
        # Wait for the flush task to complete
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=0.3)

        assert http_stream.count == 0
        assert http_stream.sequence == 2
        mock_api_client.conversations.activities().create.assert_called_once()
        sent_activity = mock_api_client.conversations.activities().create.call_args[0][0]
        assert isinstance(sent_activity, TypingActivityInput)
        assert sent_activity.text == "Hello world!"

    @pytest.mark.asyncio
    async def test_close_stream(self, http_stream):
        http_stream.emit("Final message")
        # Wait for the flush task to complete
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=0.3)

        result = await http_stream.close()

        assert result is not None
        assert isinstance(result, Resource)
        assert http_stream.closed

    @pytest.mark.asyncio
    async def test_close_empty_stream(self, http_stream):
        """Test closing an empty stream."""
        # Ensure no emit has occurred
        assert http_stream.count == 0
        assert not http_stream.closed

        result = await http_stream.close()

        # No activity was sent, so _result should remain None
        assert result is None
        assert not http_stream.closed

    @pytest.mark.asyncio
    async def test_close_already_closed(self, http_stream):
        """Test closing an already closed stream."""
        expected_result = Resource(id="test-id")
        http_stream._result = expected_result

        result = await http_stream.close()

        # Should return the previously stored result without sending again
        assert result == expected_result

    @pytest.mark.asyncio
    async def test_flush_multiple_sequences(self, http_stream, mock_api_client):
        """Test flushing multiple messages (batching)."""

        for i in range(15):  # More than the batch size
            http_stream.emit(f"Message {i}")

        # Wait for the flush task to complete
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=0.3)

        # Should have processed 10 messages and left 5 in the queue
        assert http_stream.count == 5
        assert http_stream.sequence == 2
        # Confirm that combined string contains the first 10 messages
        expected_text = "".join([f"Message {i}" for i in range(10)])
        args = mock_api_client.conversations.activities().create.call_args[0]
        assert expected_text in args[0].text
        assert http_stream._id == "mock-id"

        # Check that the remaining messages are also flushed
        await asyncio.wait_for(http_stream._delayed_flush(), timeout=0.3)
        assert http_stream.count == 0
        assert http_stream.sequence == 3
        # Confirm that combined string contains the last 5 messages
        expected_text = "".join([f"Message {i}" for i in range(15)])
        args = mock_api_client.conversations.activities().create.call_args[0]
        assert expected_text in args[0].text
        assert http_stream._id == "mock-id"

    def test_events_emitter(self, http_stream):
        """Test that events emitter is available and emits events properly."""
        assert http_stream._events is not None

        mock_listener = MagicMock()
        http_stream._events.on("chunk", mock_listener)

        test_data = {"test": "data"}
        http_stream._events.emit("chunk", test_data)

        mock_listener.assert_called_once_with(test_data)


class TestStreamingIntegration:
    """Integration tests for complete streaming workflow."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def conversation_reference(self):
        return ConversationReference(
            service_url="https://smba.trafficmanager.net/teams/",
            bot=Account(id="test-bot", name="Test Bot"),
            conversation=ConversationAccount(id="test-conversation", conversation_type="personal"),
            activity_id="test-activity",
            channel_id="msteams",
        )

    @pytest.mark.asyncio
    async def test_complete_streaming_workflow(self, mock_logger, conversation_reference):
        """Test a complete streaming workflow from start to finish."""
        # Create mock API client with full method chain
        mock_api_client = MagicMock(spec=ApiClient)

        # Mock conversations.activities().create/update
        mock_activities = MagicMock()
        mock_conversations = MagicMock()
        mock_conversations.activities.return_value = mock_activities
        mock_api_client.conversations = mock_conversations

        mock_activities.create = AsyncMock(return_value=Resource(id="mock-id"))
        mock_activities.update = AsyncMock(return_value=Resource(id="mock-id"))

        # Create stream
        stream = HttpStream(mock_api_client, conversation_reference, mock_logger)

        # Simulate streaming workflow
        stream.emit("Hello")
        stream.emit(" world!")
        await asyncio.wait_for(stream._delayed_flush(), timeout=0.3)

        assert mock_activities.create.call_count == 1
        expected_text = "Hello world!"
        args = mock_activities.create.call_args[0]
        assert isinstance(args[0], TypingActivityInput)
        assert args[0].text == expected_text
        assert stream.count == 0
        assert stream.sequence == 2
        assert stream._id == "mock-id"

        stream.emit("Bye!")
        await asyncio.wait_for(stream._delayed_flush(), timeout=0.3)

        assert mock_activities.create.call_count == 2
        expected_text = "Hello world!Bye!"
        args = mock_activities.create.call_args[0]
        assert isinstance(args[0], TypingActivityInput)
        assert args[0].text == expected_text
        assert stream.count == 0
        assert stream.sequence == 3
        assert stream._id == "mock-id"

        # Close the stream
        await stream.close()
        assert mock_activities.create.call_count == 3
        expected_text = "Hello world!Bye!"
        args = mock_activities.create.call_args[0]
        assert isinstance(args[0], MessageActivityInput)
        assert args[0].text == expected_text
        assert stream.count == 0
        assert stream.sequence == 1
        assert stream._id is None
        assert stream.closed
