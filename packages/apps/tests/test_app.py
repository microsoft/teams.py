"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
import importlib.metadata
import os
import re
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import (
    Account,
    ConversationAccount,
    FederatedIdentityCredentials,
    InvokeActivity,
    ManagedIdentityCredentials,
    MessageActivity,
    MessageActivityInput,
    SentActivity,
    TokenCredentials,
    TokenProtocol,
    TypingActivity,
)
from microsoft_teams.apps import ActivityContext, ActivityEvent, App, AppOptions, Plugin, PluginBase, PluginStartEvent
from microsoft_teams.apps.events import CoreActivity


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
    def basic_options(self, mock_storage):
        """Create basic app options."""
        return AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )

    def _mock_http_server(self, app: App) -> App:
        """Helper to mock the HTTP server methods."""
        app.server.adapter.start = AsyncMock()  # type: ignore[method-assign]
        app.server.adapter.stop = AsyncMock()  # type: ignore[method-assign]
        return app

    @pytest.fixture(scope="function")
    def app_with_options(self, basic_options):
        """Create App with basic options."""
        app = App(**basic_options)
        return self._mock_http_server(app)

    @pytest.fixture(scope="function")
    def app_with_activity_handler(self, mock_storage, mock_activity_handler):
        """Create App with activity handler."""
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
            plugins=[],
        )
        app = App(**options)
        app.on_activity(mock_activity_handler)
        return self._mock_http_server(app)

    def test_app_starts_successfully(self, basic_options):
        """Test that app can be created and initialized."""
        app = App(**basic_options)

        # Basic functional test - app should be created
        assert app.port is None

    @pytest.mark.asyncio
    async def test_app_lifecycle_start_stop(self, app_with_options):
        """Test basic app lifecycle: start and stop."""

        # Test start — server.adapter.start is already mocked by _mock_http_server
        start_task = asyncio.create_task(app_with_options.start(3978))
        await asyncio.sleep(0.1)

        assert app_with_options.port == 3978

        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        # Test stop
        await app_with_options.stop()

    @pytest.mark.asyncio
    async def test_app_start_with_multiple_plugins_cancelled(self, mock_storage):
        @Plugin(name="PluginTwo", version="1.0", description="plugin")
        class PluginTwo(PluginBase):
            def __init__(self):
                super().__init__()
                self.stop_called = False

            async def on_start(self, event: PluginStartEvent) -> None:  # noqa: D102
                pass

            async def on_stop(self) -> None:  # noqa: D102
                self.stop_called = True

        plugin_two = PluginTwo()

        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
            plugins=[plugin_two],
        )
        app = App(**options)

        # Mock server.start to block until cancelled
        block = asyncio.Event()

        async def blocking_start(port):
            await block.wait()

        app.server.adapter.start = AsyncMock(side_effect=blocking_start)  # type: ignore[method-assign]
        app.server.adapter.stop = AsyncMock()  # type: ignore[method-assign]

        start_task = asyncio.create_task(app.start(3978))
        await asyncio.sleep(0.1)

        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        assert plugin_two.stop_called, "plugin two on_stop was called."

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

        core_activity = CoreActivity(
            type="message",
            id="test-activity-id",
        )

        await app_with_activity_handler.event_manager.on_activity(ActivityEvent(body=core_activity, token=FakeToken()))

        # Wait for the async event handler to complete
        await asyncio.wait_for(event_received.wait(), timeout=1.0)

        # Verify event was emitted
        assert len(activity_events) == 1
        assert isinstance(activity_events[0], ActivityEvent)
        # The event contains the core activity
        assert activity_events[0].body.id == core_activity.id
        assert activity_events[0].body.type == core_activity.type

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

        core_activity = CoreActivity(
            type="message",
            id="test-activity-id",
        )

        await app_with_options.event_manager.on_activity(ActivityEvent(body=core_activity, token=FakeToken()))

        # Wait for both async event handlers to complete
        await asyncio.wait_for(both_received.wait(), timeout=1.0)

        # Both handlers should have received the event
        assert len(activity_events_1) == 1
        assert len(activity_events_2) == 1
        assert activity_events_1[0].body == core_activity
        assert activity_events_2[0].body == core_activity

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

    @pytest.mark.asyncio
    async def test_app_with_callable_token(self):
        """Test that app initializes with callable token."""
        token_called = False

        def get_token(scope, tenant_id=None):
            nonlocal token_called
            token_called = True
            return "test.jwt.token"

        options = AppOptions(client_id="test-client-123", token=get_token)

        # Mock environment variables to ensure they don't interfere
        with patch.dict("os.environ", {"CLIENT_ID": "", "CLIENT_SECRET": "", "TENANT_ID": ""}, clear=False):
            app = App(**options)

            assert app.credentials is not None
            assert type(app.credentials) is TokenCredentials
            assert app.credentials.client_id == "test-client-123"
            assert callable(app.credentials.token)

            res = await app.api.bots.token.get(app.credentials)
            assert token_called is True
            assert res.access_token == "test.jwt.token"

    def test_middleware_registration(self, app_with_options: App) -> None:
        """Test that middleware is registered correctly using app.use()."""

        async def logging_middleware(ctx: ActivityContext) -> None:
            await ctx.next()

        app_with_options.use(logging_middleware)

        from_account = Account(id="bot-123", name="Test Bot", role="bot")
        recipient = Account(id="user-456", name="Test User", role="user")
        conversation = ConversationAccount(id="conv-789", conversation_type="personal")

        message_activity = MessageActivity(
            id="test-activity-id",
            type="message",
            text="hello world",
            from_=from_account,
            recipient=recipient,
            conversation=conversation,
            channel_id="msteams",
        )

        handlers = app_with_options.router.select_handlers(message_activity)
        assert len(handlers) == 1
        assert handlers[0] == logging_middleware

    @pytest.mark.asyncio
    async def test_func_decorator_registration(self, app_with_options: App):
        """Simple test that @app.func registers a function."""
        mock_register = MagicMock()
        app_with_options.server.adapter.register_route = mock_register  # type: ignore[method-assign]

        async def dummy_func(ctx):
            return "called"

        decorated = app_with_options.func(dummy_func)
        assert decorated == dummy_func

        # Extract the endpoint path it was registered to
        mock_register.assert_called_once()
        method, path, handler = mock_register.call_args[0]
        assert method == "POST"
        assert path == f"/api/functions/{dummy_func.__name__.replace('_', '-')}"

    def test_user_agent_format(self, app_with_options: App):
        """Test that USER_AGENT follows the expected format teams.py[apps]/{version}."""
        version = importlib.metadata.version("microsoft-teams-apps")
        expected_user_agent = f"teams.py[apps]/{version}"

        # Verify the http_client has the correct User-Agent header
        assert "User-Agent" in app_with_options.http_client._options.headers
        assert app_with_options.http_client._options.headers["User-Agent"] == expected_user_agent

    @pytest.mark.parametrize(
        "options_dict,env_vars,expected_client_id,expected_tenant_id,description",
        [
            # Inferred from client_id only
            (
                {"client_id": "test-managed-identity-client-id"},
                {"CLIENT_SECRET": "", "TENANT_ID": "test-tenant-id"},
                "test-managed-identity-client-id",
                "test-tenant-id",
                "inferred from client_id only",
            ),
            # managed_identity_client_id equals client_id (valid)
            (
                {"client_id": "test-client-id", "managed_identity_client_id": "test-client-id"},
                {"CLIENT_SECRET": "", "TENANT_ID": "test-tenant-id"},
                "test-client-id",
                "test-tenant-id",
                "managed_identity_client_id equals client_id",
            ),
            # From environment variables
            (
                {},
                {"CLIENT_ID": "env-managed-identity-client-id", "CLIENT_SECRET": "", "TENANT_ID": "env-tenant-id"},
                "env-managed-identity-client-id",
                "env-tenant-id",
                "from environment variables",
            ),
            # Explicit managed_identity_client_id
            (
                {
                    "client_id": "test-app-id",
                    "managed_identity_client_id": "test-app-id",
                    "tenant_id": "test-tenant-id",
                },
                {"CLIENT_SECRET": ""},
                "test-app-id",
                "test-tenant-id",
                "explicit managed_identity_client_id",
            ),
        ],
    )
    def test_app_init_with_managed_identity(
        self,
        mock_storage,
        options_dict: dict,
        env_vars: dict,
        expected_client_id: str,
        expected_tenant_id: str,
        description: str,
    ):
        """Test app initialization with managed identity credentials."""
        options = AppOptions(storage=mock_storage, **options_dict)

        with patch.dict("os.environ", env_vars, clear=False):
            app = App(**options)

            assert app.credentials is not None, f"Failed for: {description}"
            assert isinstance(app.credentials, ManagedIdentityCredentials), f"Failed for: {description}"
            assert app.credentials.client_id == expected_client_id, f"Failed for: {description}"
            assert app.credentials.tenant_id == expected_tenant_id, f"Failed for: {description}"

    @pytest.mark.parametrize(
        "managed_identity_client_id,expected_mi_type,expected_mi_client_id,description",
        [
            # System-assigned managed identity
            ("system", "system", None, "system-assigned managed identity"),
            # User-assigned managed identity (federated)
            (
                "different-managed-identity-id",
                "user",
                "different-managed-identity-id",
                "user-assigned federated identity",
            ),
        ],
    )
    def test_app_init_with_federated_identity(
        self,
        mock_storage,
        managed_identity_client_id: str,
        expected_mi_type: str,
        expected_mi_client_id: str | None,
        description: str,
    ):
        """Test app initialization with FederatedIdentityCredentials."""
        options = AppOptions(
            storage=mock_storage,
            client_id="app-client-id",
            managed_identity_client_id=managed_identity_client_id,
        )

        with patch.dict("os.environ", {"CLIENT_SECRET": "", "TENANT_ID": "test-tenant-id"}, clear=False):
            app = App(**options)

            assert app.credentials is not None, f"Failed for: {description}"
            assert isinstance(app.credentials, FederatedIdentityCredentials), f"Failed for: {description}"
            assert app.credentials.client_id == "app-client-id", f"Failed for: {description}"
            assert app.credentials.managed_identity_type == expected_mi_type, f"Failed for: {description}"
            assert app.credentials.managed_identity_client_id == expected_mi_client_id, f"Failed for: {description}"
            assert app.credentials.tenant_id == "test-tenant-id", f"Failed for: {description}"

    def test_app_init_with_client_secret_takes_precedence(self, mock_storage):
        """Test that ClientCredentials is used when both client_secret and managed_identity_client_id are provided."""
        # When client_secret is provided, it should take precedence over managed identity
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
            managed_identity_client_id="test-managed-id",  # This should be ignored
            tenant_id="test-tenant-id",
        )

        app = App(**options)

        assert app.credentials is not None
        # Should use ClientCredentials, not ManagedIdentityCredentials
        assert type(app.credentials).__name__ == "ClientCredentials"
        assert app.credentials.client_id == "test-client-id"

    def test_service_url_default(self, mock_storage):
        """Test that app uses default service URL when no configuration provided."""
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        with patch.dict("os.environ", {}, clear=False):
            # Ensure SERVICE_URL is not in environment
            if "SERVICE_URL" in os.environ:
                del os.environ["SERVICE_URL"]

            app = App(**options)
            assert app.api.service_url == "https://smba.trafficmanager.net/teams"

    def test_service_url_from_environment(self, mock_storage):
        """Test that app uses service URL from environment variable."""
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        with patch.dict("os.environ", {"SERVICE_URL": "https://custom.service.url/teams"}, clear=False):
            app = App(**options)
            assert app.api.service_url == "https://custom.service.url/teams"

    def test_service_url_from_options(self, mock_storage):
        """Test that app uses service URL from options when provided."""
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
            service_url="https://options.service.url/teams",
        )

        with patch.dict("os.environ", {"SERVICE_URL": "https://env.service.url/teams"}, clear=False):
            app = App(**options)
            # Options should take precedence over environment
            assert app.api.service_url == "https://options.service.url/teams"

    def test_service_url_priority(self, mock_storage):
        """Test that service URL prioritizes options > env > default."""
        # Test 1: Default when neither option nor env provided
        options1 = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        with patch.dict("os.environ", {}, clear=False):
            if "SERVICE_URL" in os.environ:
                del os.environ["SERVICE_URL"]
            app1 = App(**options1)
            assert app1.api.service_url == "https://smba.trafficmanager.net/teams"

        # Test 2: Environment when provided but option not set
        options2 = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        with patch.dict("os.environ", {"SERVICE_URL": "https://env.service.url/teams"}, clear=False):
            app2 = App(**options2)
            assert app2.api.service_url == "https://env.service.url/teams"

        # Test 3: Options when both option and env provided
        options3 = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-client-secret",
            service_url="https://options.service.url/teams",
        )

        with patch.dict("os.environ", {"SERVICE_URL": "https://env.service.url/teams"}, clear=False):
            app3 = App(**options3)
            assert app3.api.service_url == "https://options.service.url/teams"

    # Tests for App.send() proactive targeted message validation

    @pytest.mark.asyncio
    async def test_proactive_targeted_without_recipient_raises_error(self, mock_storage) -> None:
        """
        Test that sending a targeted message proactively without an explicit
        recipient raises a ValueError.
        """
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )
        app = App(**options)
        app._initialized = True
        app.activity_sender.send = AsyncMock(
            return_value=SentActivity(id="sent-activity-id", activity_params=MessageActivityInput(text="sent"))
        )

        # Create a targeted message without explicit recipient
        activity = MessageActivityInput(text="Hello")
        activity.is_targeted = True  # Set is_targeted without recipient

        with pytest.raises(
            ValueError, match="Targeted messages sent proactively must specify an explicit recipient account"
        ):
            await app.send("conv-123", activity)

    @pytest.mark.asyncio
    async def test_proactive_targeted_with_explicit_recipient_succeeds(self, mock_storage) -> None:
        """
        Test that sending a targeted message proactively with an explicit
        recipient account succeeds.
        """
        options = AppOptions(
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )
        app = App(**options)
        app._initialized = True
        app.activity_sender.send = AsyncMock(
            return_value=SentActivity(id="sent-activity-id", activity_params=MessageActivityInput(text="sent"))
        )

        # Create a targeted message with explicit recipient
        recipient = Account(id="user-456", name="Test User", role="user")
        activity = MessageActivityInput(text="Hello").with_recipient(recipient, is_targeted=True)

        # Should not raise - explicit recipient provided
        result = await app.send("conv-123", activity)

        app.activity_sender.send.assert_called_once()
        assert result.id == "sent-activity-id"
