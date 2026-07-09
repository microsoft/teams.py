"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.api import (
    Activity,
    ActivityBase,
    ConversationReference,
    InvokeResponse,
    TokenProtocol,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.apps import ActivityContext, ActivityEvent
from microsoft_teams.apps.activity_sender import ActivitySender
from microsoft_teams.apps.app_events import EventManager
from microsoft_teams.apps.app_process import ActivityProcessor
from microsoft_teams.apps.events import CoreActivity
from microsoft_teams.apps.routing.router import ActivityHandler, ActivityRouter
from microsoft_teams.apps.token_manager import TokenManager
from microsoft_teams.common import Client, LocalStorage


class TestActivityProcessor:
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_http_client(self):
        http_client = MagicMock(spec=Client)
        http_client.clone.return_value = http_client
        return http_client

    @pytest.fixture
    def activity_processor(self, mock_http_client):
        """Create an ActivityProcessor instance."""
        mock_storage = MagicMock(spec=LocalStorage)
        mock_activity_router = MagicMock(spec=ActivityRouter)
        mock_token_manager = MagicMock(spec=TokenManager)
        mock_activity_sender = MagicMock(spec=ActivitySender)
        # Mock the stream object with async close
        mock_stream = MagicMock()
        mock_stream.close = AsyncMock()
        mock_activity_sender.create_stream.return_value = mock_stream
        return ActivityProcessor(
            mock_activity_router,
            "id",
            mock_storage,
            "default_connection",
            mock_http_client,
            mock_token_manager,
            None,
            mock_activity_sender,
            PUBLIC,
        )

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_with_no_handlers(self, activity_processor):
        """Test the process_activity method with no handlers."""
        context = MagicMock(spec=ActivityContext)
        activity_processor.event_manager = MagicMock(spec=EventManager)

        response = await activity_processor.execute_middleware_chain(context, [])
        assert response is None

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_with_two_handlers(self, activity_processor, mock_http_client):
        """Test the execute_middleware_chain method with two handlers."""
        mock_activity_sender = MagicMock(spec=ActivitySender)
        mock_activity_sender.create_stream.return_value = MagicMock()
        context = ActivityContext(
            activity=MagicMock(spec=ActivityBase),
            app_id="app_id",
            storage=MagicMock(spec=LocalStorage),
            api=mock_http_client,
            user_token=None,
            conversation_ref=MagicMock(spec=ConversationReference),
            is_signed_in=True,
            connection_name="default_connection",
            activity_sender=mock_activity_sender,
            app_token=lambda: None,
            cloud=PUBLIC,
        )

        handler_one = AsyncMock(spec=ActivityHandler)

        async def handler_one_side_effect(ctx: ActivityContext[Activity]) -> str:
            await ctx.next()
            return "handler_one"

        handler_one.side_effect = handler_one_side_effect

        handler_two = AsyncMock(spec=ActivityHandler)

        async def handler_two_side_effect(ctx: ActivityContext[Activity]) -> str:
            await ctx.next()
            return "handler_two"

        handler_two.side_effect = handler_two_side_effect
        handlers = [handler_one, handler_two]

        response = await activity_processor.execute_middleware_chain(context, handlers)
        handler_one.assert_called_once_with(context)
        handler_two.assert_called_once_with(context)
        assert response == "handler_one"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "middleware_result, expected_result",
        [
            (None, InvokeResponse(status=200, body=None)),
            ({"key": "value"}, InvokeResponse[Any](status=200, body={"key": "value"})),
            (
                InvokeResponse[Any](status=201, body={"custom": "response"}),
                InvokeResponse[Any](status=201, body={"custom": "response"}),
            ),
        ],
    )
    async def test_process_activity_middleware_results(self, activity_processor, middleware_result, expected_result):
        """Test process_activity with different middleware return values."""
        # Setup mocks
        mock_plugins = []

        # Create core activity with required fields for MessageActivity
        core_activity = CoreActivity(
            type="message",
            id="activity-123",
            service_url="https://service.url",
            **{
                "from": {"id": "user-123", "name": "Test User"},
                "conversation": {"id": "conv-789"},
                "recipient": {"id": "bot-456", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        # Setup processor mocks
        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.execute_middleware_chain = AsyncMock(return_value=middleware_result)
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        # Act
        result = await activity_processor.process_activity(mock_plugins, mock_activity_event)

        # Assert
        assert result.status == expected_result.status
        assert result.body == expected_result.body

    @pytest.mark.asyncio
    async def test_process_activity_invokes_plugin_route_when_plugin_qualifies(self, activity_processor):
        """Plugins with on_activity_event get wrapped in a route that calls plugin.on_activity."""
        core_activity = CoreActivity(
            type="message",
            id="activity-plugin",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        # Plugin with the qualifying attrs (on_activity_event hasattr + callable on_activity)
        qualifying_plugin = MagicMock()
        qualifying_plugin.on_activity_event = MagicMock()
        qualifying_plugin.on_activity = AsyncMock()

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        await activity_processor.process_activity([qualifying_plugin], mock_activity_event)

        qualifying_plugin.on_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_updated_send_emits_activity_sent_event(self, activity_processor):
        """Handler invoking ctx.send triggers updated_send -> event_manager.on_activity_sent."""
        from microsoft_teams.api import MessageActivityInput, SentActivity

        core_activity = CoreActivity(
            type="message",
            id="activity-send",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        # Activity sender returns a SentActivity from send()
        sent = SentActivity(id="sent-1", activity_params=MessageActivityInput(text="hi"))
        activity_processor.activity_sender.send = AsyncMock(return_value=sent)

        # Handler that calls ctx.send to exercise the updated_send wrapper
        async def calling_handler(ctx):
            await ctx.send("hi")
            return None

        activity_processor.router.select_handlers = MagicMock(return_value=[calling_handler])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_activity_sent = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        await activity_processor.process_activity([], mock_activity_event)

        activity_processor.event_manager.on_activity_sent.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_handlers_emit_activity_sent_events(self, activity_processor):
        """handle_chunk and handle_close emit on_activity_sent for stream events."""
        from microsoft_teams.api import MessageActivityInput, SentActivity

        core_activity = CoreActivity(
            type="message",
            id="activity-stream",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        mock_stream = activity_processor.activity_sender.create_stream.return_value

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_activity_sent = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        await activity_processor.process_activity([], mock_activity_event)

        # Stream's on_chunk and on_close were registered with the inner handlers.
        # Invoke them to exercise their bodies.
        chunk_handler = mock_stream.on_chunk.call_args[0][0]
        close_handler = mock_stream.on_close.call_args[0][0]

        sent = SentActivity(id="chunk-1", activity_params=MessageActivityInput(text="chunk"))
        await chunk_handler(sent)
        await close_handler(sent)

        assert activity_processor.event_manager.on_activity_sent.call_count == 2

    @pytest.mark.asyncio
    async def test_build_context_marks_signed_in_when_token_available(self, activity_processor):
        """When the token API returns a token, ActivityContext is built with is_signed_in=True."""
        from unittest.mock import patch

        core_activity = CoreActivity(
            type="message",
            id="activity-token",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        # Patch ApiClient so users.get_token returns a successful response
        token_response = MagicMock()
        token_response.token = "user-jwt-token"
        mock_api_client = MagicMock()
        mock_api_client.users.get_token = AsyncMock(return_value=token_response)

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        with patch("microsoft_teams.apps.app_process.ApiClient", return_value=mock_api_client):
            await activity_processor.process_activity([], mock_activity_event)

        mock_api_client.users.get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_activity_raises_when_event_manager_missing(self, activity_processor):
        """process_activity raises ValueError if event_manager was never initialized."""
        core_activity = CoreActivity(
            type="message",
            id="activity-no-em",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        # Intentionally do NOT set event_manager - keep it as None

        with pytest.raises(ValueError, match="EventManager was not initialized"):
            await activity_processor.process_activity([], mock_activity_event)

    @pytest.mark.asyncio
    async def test_process_activity_handles_stream_cancelled(self, activity_processor):
        """StreamCancelledError from middleware is caught; response status is 200."""
        from microsoft_teams.apps.plugins import StreamCancelledError

        core_activity = CoreActivity(
            type="message",
            id="activity-cancel",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.execute_middleware_chain = AsyncMock(side_effect=StreamCancelledError())
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        result = await activity_processor.process_activity([], mock_activity_event)

        assert result.status == 200

    @pytest.mark.asyncio
    async def test_process_activity_raises_exception(self, activity_processor):
        """Test process_activity raises exception when middleware chain fails."""
        # Setup mocks
        mock_plugins = []

        # Create core activity with required fields for MessageActivity
        core_activity = CoreActivity(
            type="message",
            id="activity-123",
            service_url="https://service.url",
            **{
                "from": {"id": "user-123", "name": "Test User"},
                "conversation": {"id": "conv-789"},
                "recipient": {"id": "bot-456", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        # Setup processor mocks
        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.execute_middleware_chain = AsyncMock()
        test_exception = Exception("Test exception")
        activity_processor.execute_middleware_chain.side_effect = test_exception
        activity_processor.event_manager = AsyncMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()

        # Act & Assert - expect exception to be raised
        with pytest.raises(Exception, match="Test exception"):
            await activity_processor.process_activity(mock_plugins, mock_activity_event)

        # Assert error event was called
        assert activity_processor.event_manager.on_error.called
