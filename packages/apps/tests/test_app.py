"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft.teams.api import TokenProtocol
from microsoft.teams.api.activities import InvokeActivity
from microsoft.teams.api.activities.message import MessageActivity
from microsoft.teams.api.activities.typing import TypingActivity
from microsoft.teams.api.models import Account, ConversationAccount
from microsoft.teams.apps.app import App
from microsoft.teams.apps.events import ActivityEvent
from microsoft.teams.apps.options import AppOptions
from microsoft.teams.apps.routing.activity_context import ActivityContext


class FakeToken(TokenProtocol):
    """Fake token for testing."""

    @property
    def app_id(self) -> str:
        return "test-app-id"

    @property
    def app_display_name(self) -> Optional[str]:
        return "Test App"

    @property
    def tenant_id(self) -> Optional[str]:
        return "test-tenant-id"

    @property
    def service_url(self) -> str:
        return "https://test.service.url"

    @property
    def from_(self) -> str:
        return "azure"

    @property
    def from_id(self) -> str:
        return "test-from-id"

    @property
    def expiration(self) -> Optional[int]:
        return None

    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        return False

    def __str__(self) -> str:
        return "FakeToken"


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

        async def handler(ctx) -> None:
            pass

        return handler

    @pytest.fixture(scope="function")
    def basic_options(self, mock_logger, mock_storage):
        """Create basic app options."""
        return AppOptions(
            logger=mock_logger,
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )

    @pytest.fixture(scope="function")
    def app_with_options(self, basic_options):
        """Create App with basic options."""
        return App(basic_options)

    @pytest.fixture(scope="function")
    def app_with_activity_handler(self, mock_logger, mock_storage, mock_activity_handler):
        """Create App with activity handler."""
        options = AppOptions(
            logger=mock_logger,
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
            plugins=[],
        )
        app = App(options)
        app.on_activity(mock_activity_handler)
        return app

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
            type="message",
            id="test-activity-id",
            text="Hello, world!",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        plugin = app_with_activity_handler.http

        await app_with_activity_handler.event_manager.on_activity(
            ActivityEvent(activity=activity, sender=plugin, token=FakeToken()), plugins=[plugin]
        )

        # Wait for the async event handler to complete
        await asyncio.wait_for(event_received.wait(), timeout=1.0)

        # Verify event was emitted
        assert len(activity_events) == 1
        assert isinstance(activity_events[0], ActivityEvent)
        # The event contains the parsed output model, not the input model
        assert activity_events[0].activity.id == activity.id
        assert activity_events[0].activity.type == activity.type
        # Check text only if it's a MessageActivity
        if hasattr(activity_events[0].activity, "text"):
            assert activity_events[0].activity.text == activity.text

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
            type="message",
            id="test-activity-id",
            text="Hello, world!",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        await app_with_options.event_manager.on_activity(
            ActivityEvent(activity=activity, sender=app_with_options.http, token=FakeToken()),
            plugins=[app_with_options.http],
        )

        # Wait for both async event handlers to complete
        await asyncio.wait_for(both_received.wait(), timeout=1.0)

        # Both handlers should have received the event
        assert len(activity_events_1) == 1
        assert len(activity_events_2) == 1
        assert activity_events_1[0].activity == activity
        assert activity_events_2[0].activity == activity

    # Generated Handler Tests

    def test_generated_handler_registration(self, app_with_options: App) -> None:
        """Test that generated handlers register correctly in the router."""

        @app_with_options.on_message
        async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
            assert ctx.activity.type == "message"

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        message_activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="Hello from generated handler!",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Verify handler was registered
        message_handlers = app_with_options.router.select_handlers(message_activity)
        assert len(message_handlers) == 1
        assert message_handlers[0] == handle_message

    def test_multiple_handlers_same_type(self, app_with_options: App) -> None:
        """Test that multiple handlers can be registered for the same activity type."""

        @app_with_options.on_message
        async def handle_message_1(ctx: ActivityContext[MessageActivity]) -> None:
            pass

        @app_with_options.on_message
        async def handle_message_2(ctx: ActivityContext[MessageActivity]) -> None:
            pass

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        message_activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="Hello from generated handler!",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Verify both handlers were registered
        message_handlers = app_with_options.router.select_handlers(message_activity)
        assert len(message_handlers) == 2
        assert handle_message_1 in message_handlers
        assert handle_message_2 in message_handlers

    def test_different_activity_types_separate_routes(self, app_with_options: App) -> None:
        """Test that different activity types are routed separately."""

        @app_with_options.on_message
        async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
            pass

        @app_with_options.on_typing
        async def handle_typing(ctx: ActivityContext[TypingActivity]) -> None:
            pass

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        message_activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="Hello from generated handler!",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        typing_activity = TypingActivity(
            id="test-typing-id",
            type="typing",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Verify handlers are in separate routes
        message_handlers = app_with_options.router.select_handlers(message_activity)
        typing_handlers = app_with_options.router.select_handlers(typing_activity)

        assert len(message_handlers) == 1
        assert len(typing_handlers) == 1
        assert message_handlers[0] == handle_message
        assert typing_handlers[0] == handle_typing

    @pytest.mark.asyncio
    async def test_generated_handler_execution(self, app_with_options: App) -> None:
        """Test that generated handlers are executed correctly."""
        handler_data = {}

        @app_with_options.on_message
        async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
            handler_data["called"] = True
            handler_data["activity_text"] = ctx.activity.text

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="Hello from generated handler!",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
        )

        # Mock the HTTP plugin response method
        app_with_options.http.on_activity_response = AsyncMock()

        await app_with_options.event_manager.on_activity(
            ActivityEvent(activity=activity, sender=app_with_options.http, token=FakeToken()),
            plugins=[app_with_options.http],
        )

        # Verify handler was called and executed
        assert handler_data["called"] is True
        assert handler_data["activity_text"] == "Hello from generated handler!"

    def test_runtime_type_validation(self, app_with_options: App) -> None:
        """Test that runtime type validation catches incorrect type annotations."""
        with pytest.raises(TypeError) as exc_info:

            @app_with_options.on_message  # type: ignore
            async def handle_wrong_type(ctx: ActivityContext[InvokeActivity]) -> None:  # Wrong type!
                pass

        # Verify the error message mentions the type mismatch
        error_msg = str(exc_info.value)
        assert "InvokeActivity" in error_msg
        assert "MessageActivity" in error_msg
        assert "on_message" in error_msg

    def test_on_message_pattern_string_match(self, app_with_options: App) -> None:
        """Test on_message_pattern with string pattern matching."""

        @app_with_options.on_message_pattern("hello world")
        async def handle_hello(ctx: ActivityContext[MessageActivity]) -> None:
            pass

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test matching message
        matching_activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="hello world",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Test non-matching message
        non_matching_activity = MessageActivity(
            id="test-activity-id-2",
            type="message",
            text="goodbye world",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Verify handler was registered and can match
        handlers = app_with_options.router.select_handlers(matching_activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_hello

        # Verify non-matching activity doesn't match
        non_matching_handlers = app_with_options.router.select_handlers(non_matching_activity)
        assert len(non_matching_handlers) == 0

    def test_on_message_pattern_regex_match(self, app_with_options: App) -> None:
        """Test on_message_pattern with regex pattern matching."""
        import re

        @app_with_options.on_message_pattern(re.compile(r"hello \w+"))
        async def handle_hello_pattern(ctx: ActivityContext[MessageActivity]) -> None:
            pass

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        # Test matching message
        matching_activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="hello world",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Test non-matching message
        non_matching_activity = MessageActivity(
            id="test-activity-id-2",
            type="message",
            text="hello",  # Missing word after hello
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        # Verify handler was registered and can match
        handlers = app_with_options.router.select_handlers(matching_activity)
        assert len(handlers) == 1
        assert handlers[0] == handle_hello_pattern

        # Verify non-matching activity doesn't match
        non_matching_handlers = app_with_options.router.select_handlers(non_matching_activity)
        assert len(non_matching_handlers) == 0
