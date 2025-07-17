"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft.teams.api import ActivityBase
from microsoft.teams.api.activities.message import MessageActivity
from microsoft.teams.api.models import Account, ConversationAccount
from microsoft.teams.app.app import App
from microsoft.teams.app.events import ActivityEvent, ErrorEvent
from microsoft.teams.app.options import AppOptions


class TestApp:
    """Test cases for App class public interface."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage."""
        return MagicMock()

    @pytest.fixture
    def mock_activity_handler(self):
        """Create a mock activity handler."""

        async def handler(activity: ActivityBase) -> dict[str, str]:
            return {"status": "handled", "activityId": activity.id}

        return handler

    @pytest.fixture
    def basic_options(self, mock_logger, mock_storage):
        """Create basic app options."""
        return AppOptions(
            logger=mock_logger,
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )

    @pytest.fixture
    def app_with_options(self, basic_options):
        """Create App with basic options."""
        return App(basic_options)

    @pytest.fixture
    def app_with_activity_handler(self, basic_options, mock_activity_handler):
        """Create App with activity handler."""
        basic_options.activity_handler = mock_activity_handler
        return App(basic_options)

    def test_app_starts_successfully(self, basic_options):
        """Test that app can be created and initialized."""
        app = App(basic_options)

        # Basic functional test - app should be created and not running
        assert not app.is_running
        assert app.port is None

    @pytest.mark.asyncio
    async def test_app_lifecycle_start_stop(self, app_with_options):
        """Test basic app lifecycle: start and stop."""
        # Mock the underlying HTTP server to avoid actual server startup
        with (
            patch.object(app_with_options, "_refresh_tokens", new_callable=AsyncMock),
            patch.object(app_with_options.http, "on_start", new_callable=AsyncMock),
        ):
            # Test start
            start_task = asyncio.create_task(app_with_options.start(3978))
            await asyncio.sleep(0.1)

            # App should be running and have correct port
            assert app_with_options.is_running
            assert app_with_options.port == 3978

            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

        # Test stop
        app_with_options._running = True

        async def mock_on_stop():
            if app_with_options.http.on_stopped_callback:
                await app_with_options.http.on_stopped_callback()

        with patch.object(app_with_options.http, "on_stop", new_callable=AsyncMock, side_effect=mock_on_stop):
            await app_with_options.stop()
            assert not app_with_options.is_running

    @pytest.mark.asyncio
    async def test_activity_processing(self, app_with_activity_handler):
        """Test that activities are processed correctly."""
        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = MessageActivity(
            value={
                "type": "message",
                "id": "test-activity-id",
                "text": "Hello, world!",
                "from_": from_account.model_dump(),
                "recipient": recipient.model_dump(),
                "conversation": conversation.model_dump(),
            }
        )

        # Mock the HTTP plugin response method
        app_with_activity_handler.http.on_activity_response = MagicMock()

        result = await app_with_activity_handler.handle_activity(activity)

        # Verify the activity was processed successfully
        assert result["status"] == "processed"
        assert result["activityId"] == "test-activity-id"

    # Event Testing - Focus on functional behavior

    @pytest.mark.asyncio
    async def test_activity_event_emission(self, app_with_activity_handler: App) -> None:
        """Test that activity events are emitted correctly."""
        activity_events = []
        event_received = asyncio.Event()

        @app_with_activity_handler.event
        async def handle_activity(event: ActivityEvent) -> None:
            activity_events.append(event)
            event_received.set()

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = MessageActivity(
            value={
                "type": "message",
                "id": "test-activity-id",
                "text": "Hello, world!",
                "from_": from_account.model_dump(),
                "recipient": recipient.model_dump(),
                "conversation": conversation.model_dump(),
            }
        )

        await app_with_activity_handler.handle_activity(activity)

        # Wait for the async event handler to complete
        await asyncio.wait_for(event_received.wait(), timeout=1.0)

        # Verify event was emitted
        assert len(activity_events) == 1
        assert isinstance(activity_events[0], ActivityEvent)
        assert activity_events[0].activity == activity

    @pytest.mark.asyncio
    async def test_error_event_emission(self, app_with_options: App) -> None:
        """Test that error events are emitted correctly."""
        error_events = []
        error_received = asyncio.Event()

        @app_with_options.event
        async def handle_error(event: ErrorEvent) -> None:
            error_events.append(event)
            error_received.set()

        # Simulate an error during activity handling
        async def failing_handler(_activity):
            raise ValueError("Test error")

        app_with_options.activity_handler = failing_handler

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = MessageActivity(
            value={
                "type": "message",
                "id": "test-activity-id",
                "text": "Hello, world!",
                "from_": from_account.model_dump(),
                "recipient": recipient.model_dump(),
                "conversation": conversation.model_dump(),
            }
        )

        with pytest.raises(ValueError):
            await app_with_options.handle_activity(activity)

        # Wait for the async error event handler to complete
        await asyncio.wait_for(error_received.wait(), timeout=1.0)

        # Verify error event was emitted
        assert len(error_events) == 1
        assert isinstance(error_events[0], ErrorEvent)
        assert isinstance(error_events[0].error, ValueError)
        assert str(error_events[0].error) == "Test error"
        assert error_events[0].context["method"] == "handle_activity"
        assert error_events[0].context["activity_id"] == "test-activity-id"

    @pytest.mark.asyncio
    async def test_multiple_event_handlers(self, app_with_options: App) -> None:
        """Test that multiple handlers can listen to the same event."""
        activity_events_1 = []
        activity_events_2 = []
        both_received = asyncio.Event()
        received_count = 0

        @app_with_options.event
        async def handle_activity_1(event: ActivityEvent) -> None:
            nonlocal received_count
            activity_events_1.append(event)
            received_count += 1
            if received_count == 2:
                both_received.set()

        @app_with_options.event
        async def handle_activity_2(event: ActivityEvent) -> None:
            nonlocal received_count
            activity_events_2.append(event)
            received_count += 1
            if received_count == 2:
                both_received.set()

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = MessageActivity(
            value={
                "type": "message",
                "id": "test-activity-id",
                "text": "Hello, world!",
                "from_": from_account.model_dump(),
                "recipient": recipient.model_dump(),
                "conversation": conversation.model_dump(),
            }
        )

        await app_with_options.handle_activity(activity)

        # Wait for both async event handlers to complete
        await asyncio.wait_for(both_received.wait(), timeout=1.0)

        # Both handlers should have received the event
        assert len(activity_events_1) == 1
        assert len(activity_events_2) == 1
        assert activity_events_1[0].activity == activity
        assert activity_events_2[0].activity == activity
