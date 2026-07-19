"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import (
    Activity,
    ActivityTypeAdapter,
    ConversationReference,
    InvokeResponse,
    TokenProtocol,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.apps import ActivityContext, ActivityEvent
from microsoft_teams.apps.app_events import EventManager
from microsoft_teams.apps.app_process import ActivityProcessor
from microsoft_teams.apps.auth_provider import AppAuthProvider
from microsoft_teams.apps.events import CoreActivity
from microsoft_teams.apps.routing.router import ActivityHandler, ActivityRouter
from microsoft_teams.apps.token_manager import TokenManager
from microsoft_teams.common import Client, LocalStorage
from opentelemetry import baggage


class RecordingSpan:
    def __init__(self, name: str, options: dict[str, Any]):
        self.name = name
        self.options = options
        self.attributes: dict[str, str] = {}
        self.exceptions: list[BaseException] = []
        self.status = None

    def set_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = value

    def record_exception(self, exception: BaseException) -> None:
        self.exceptions.append(exception)

    def set_status(self, status) -> None:
        self.status = status


class RecordingTracer:
    def __init__(self):
        self.spans: list[RecordingSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Iterator[RecordingSpan]:
        span = RecordingSpan(name, kwargs)
        self.spans.append(span)
        yield span


def _message_activity(activity_id: str = "activity-123") -> Activity:
    core_activity = CoreActivity(
        type="message",
        id=activity_id,
        service_url="https://service.url",
        **{
            "from": {"id": "user-123", "name": "Test User"},
            "conversation": {"id": "conv-789"},
            "recipient": {"id": "bot-456", "name": "Test Bot"},
            "channelId": "msteams",
        },
    )
    return ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))


def _invoke_activity(activity_id: str = "activity-invoke") -> Activity:
    core_activity = CoreActivity(
        type="invoke",
        id=activity_id,
        service_url="https://service.url",
        **{
            "name": "config/fetch",
            "value": {},
            "from": {"id": "user-123", "name": "Test User"},
            "conversation": {"id": "conv-789"},
            "recipient": {"id": "bot-456", "name": "Test Bot"},
            "channelId": "msteams",
        },
    )
    return ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))


class TestActivityProcessor:
    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_http_client(self):
        http_client = MagicMock(spec=Client)
        http_client.token = None
        http_client.clone.return_value = http_client
        return http_client

    @pytest.fixture
    def activity_processor(self, mock_http_client):
        """Create an ActivityProcessor instance."""
        mock_storage = MagicMock(spec=LocalStorage)
        mock_activity_router = MagicMock(spec=ActivityRouter)
        mock_token_manager = MagicMock(spec=TokenManager)
        mock_auth_provider = MagicMock(spec=AppAuthProvider)
        return ActivityProcessor(
            mock_activity_router,
            "id",
            mock_storage,
            "default_connection",
            mock_http_client,
            mock_token_manager,
            mock_auth_provider,
            None,
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
        api = MagicMock()
        context = ActivityContext(
            activity=_message_activity(),
            app_id="app_id",
            storage=MagicMock(spec=LocalStorage),
            api=api,
            user_token=None,
            conversation_ref=MagicMock(spec=ConversationReference),
            is_signed_in=True,
            connection_name="default_connection",
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
    async def test_process_activity_records_turn_span_metrics_and_unmatched(self, activity_processor):
        core_activity = CoreActivity(
            type="message",
            id="activity-otel",
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
        tracer = RecordingTracer()

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        with (
            patch("microsoft_teams.apps.app_process.get_tracer", return_value=tracer),
            patch("microsoft_teams.apps.app_process.record_activity_received") as record_activity_received,
            patch("microsoft_teams.apps.app_process.record_handler_unmatched") as record_handler_unmatched,
            patch("microsoft_teams.apps.app_process.record_turn_duration") as record_turn_duration,
        ):
            result = await activity_processor.process_activity([], mock_activity_event)

        assert result.status == 200
        assert [span.name for span in tracer.spans] == ["microsoft.teams.activity.process"]
        assert tracer.spans[0].options == {"record_exception": False, "set_status_on_exception": False}
        assert tracer.spans[0].attributes == {
            "activity.type": "message",
            "activity.id": "activity-otel",
            "conversation.id": "conv-789",
            "channel.id": "msteams",
            "bot.id": "bot-456",
            "service.url": "https://service.url",
        }
        record_activity_received.assert_called_once_with("message")
        record_handler_unmatched.assert_called_once_with("message", None)
        assert record_turn_duration.call_args.args[0] >= 0
        assert record_turn_duration.call_args.args[1] == "message"

    @pytest.mark.asyncio
    async def test_process_activity_applies_agent365_baggage_during_turn(self, activity_processor):
        core_activity = CoreActivity(
            type="message",
            id="activity-baggage",
            service_url="https://service.url",
            **{
                "from": {
                    "id": "user-123",
                    "aadObjectId": "caller-aad-1",
                    "name": "Caller",
                    "email": "caller@example.com",
                },
                "conversation": {"id": "conv-789"},
                "recipient": {
                    "id": "bot-456",
                    "name": "Agent",
                    "tenantId": "tenant-1",
                    "agenticAppId": "agent-app-1",
                    "agenticUserId": "agent-user-1",
                    "agenticAppBlueprintId": "blueprint-1",
                    "email": "agentic-user@example.com",
                    "userRole": "assistant",
                },
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        async def process_core(plugins, event, activity):
            assert baggage.get_baggage("microsoft.tenant.id") == "tenant-1"
            assert baggage.get_baggage("gen_ai.conversation.id") == "conv-789"
            assert baggage.get_baggage("microsoft.conversation.item.link") == "https://service.url"
            assert baggage.get_baggage("microsoft.channel.name") == "msteams"
            assert baggage.get_baggage("user.id") == "caller-aad-1"
            assert baggage.get_baggage("user.name") == "Caller"
            assert baggage.get_baggage("user.email") == "caller@example.com"
            assert baggage.get_baggage("gen_ai.agent.id") == "agent-app-1"
            assert baggage.get_baggage("gen_ai.agent.name") == "Agent"
            assert baggage.get_baggage("microsoft.agent.user.id") == "agent-user-1"
            assert baggage.get_baggage("microsoft.agent.user.email") == "agentic-user@example.com"
            assert baggage.get_baggage("gen_ai.agent.description") == "assistant"
            assert baggage.get_baggage("microsoft.a365.agent.blueprint.id") == "blueprint-1"
            return InvokeResponse[Any](status=200)

        activity_processor._process_activity_core = AsyncMock(side_effect=process_core)

        await activity_processor.process_activity([], mock_activity_event)

        assert baggage.get_baggage("microsoft.tenant.id") is None
        assert baggage.get_baggage("gen_ai.agent.id") is None

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_records_handler_span_and_metrics(self, activity_processor):
        context = ActivityContext(
            activity=_message_activity(),
            app_id="app_id",
            storage=MagicMock(spec=LocalStorage),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(spec=ConversationReference),
            is_signed_in=True,
            connection_name="default_connection",
            app_token=lambda: None,
            cloud=PUBLIC,
        )

        async def handler(ctx: ActivityContext[Activity]) -> str:
            return "handler_result"

        tracer = RecordingTracer()

        with (
            patch("microsoft_teams.apps.app_process.get_tracer", return_value=tracer),
            patch("microsoft_teams.apps.app_process.record_handler_dispatched") as record_handler_dispatched,
            patch("microsoft_teams.apps.app_process.record_handler_duration") as record_handler_duration,
        ):
            response = await activity_processor.execute_middleware_chain(context, [handler])

        assert response == "handler_result"
        assert [span.name for span in tracer.spans] == ["microsoft.teams.handler"]
        assert tracer.spans[0].options == {"record_exception": False, "set_status_on_exception": False}
        assert tracer.spans[0].attributes == {
            "handler.type": "message",
            "handler.dispatch": "type",
        }
        record_handler_dispatched.assert_called_once_with("message", "type")
        assert record_handler_duration.call_args.args[0] >= 0
        assert record_handler_duration.call_args.args[1:] == ("message", "type")

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_records_invoke_handler_tags(self, activity_processor):
        context = ActivityContext(
            activity=_invoke_activity(),
            app_id="app_id",
            storage=MagicMock(spec=LocalStorage),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(spec=ConversationReference),
            is_signed_in=True,
            connection_name="default_connection",
            app_token=lambda: None,
            cloud=PUBLIC,
        )

        async def handler(ctx: ActivityContext[Activity]) -> None:
            return None

        tracer = RecordingTracer()

        with (
            patch("microsoft_teams.apps.app_process.get_tracer", return_value=tracer),
            patch("microsoft_teams.apps.app_process.record_handler_dispatched") as record_handler_dispatched,
            patch("microsoft_teams.apps.app_process.record_handler_duration") as record_handler_duration,
        ):
            await activity_processor.execute_middleware_chain(context, [handler])

        assert tracer.spans[0].attributes == {
            "handler.type": "config/fetch",
            "handler.dispatch": "invoke",
        }
        record_handler_dispatched.assert_called_once_with("config/fetch", "invoke")
        assert record_handler_duration.call_args.args[1:] == ("config/fetch", "invoke")

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_records_handler_exception(self, activity_processor):
        context = ActivityContext(
            activity=_message_activity(),
            app_id="app_id",
            storage=MagicMock(spec=LocalStorage),
            api=MagicMock(),
            user_token=None,
            conversation_ref=MagicMock(spec=ConversationReference),
            is_signed_in=True,
            connection_name="default_connection",
            app_token=lambda: None,
            cloud=PUBLIC,
        )
        error = RuntimeError("boom")

        async def handler(ctx: ActivityContext[Activity]) -> None:
            raise error

        tracer = RecordingTracer()

        with (
            patch("microsoft_teams.apps.app_process.get_tracer", return_value=tracer),
            patch("microsoft_teams.apps.app_process.record_handler_dispatched"),
            patch("microsoft_teams.apps.app_process.record_handler_duration"),
            patch("microsoft_teams.apps.app_process.record_handler_failure") as record_handler_failure,
            patch("microsoft_teams.apps.app_process.record_exception") as record_exception,
        ):
            with pytest.raises(RuntimeError, match="boom"):
                await activity_processor.execute_middleware_chain(context, [handler])

        record_exception.assert_called_once_with(tracer.spans[0], error)
        record_handler_failure.assert_called_once_with("message", "type")

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

        # ApiClient returns a SentActivity from send()
        sent = SentActivity(id="sent-1", activity_params=MessageActivityInput(text="hi"))
        activities = MagicMock()
        activities.create = AsyncMock(return_value=sent)
        activity_processor.http_client.clone.return_value = activity_processor.http_client
        with patch("microsoft_teams.apps.app_process.ApiClient") as mock_api_client:
            mock_context_api = MagicMock()
            mock_context_api.users.token.get = AsyncMock(side_effect=Exception("no token"))
            mock_context_api.conversations.activities.return_value = activities

            async def create_activity(conversation_id: str, activity: MessageActivityInput) -> SentActivity:
                mock_context_api.conversations.activities(conversation_id)
                return await activities.create(activity)

            mock_context_api.conversations.create_activity = AsyncMock(side_effect=create_activity)
            mock_context_api.clone.return_value = mock_context_api
            mock_api_client.return_value = mock_context_api

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

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_activity_sent = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as mock_stream_class:
            mock_stream = mock_stream_class.return_value
            mock_stream.close = AsyncMock()

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
    async def test_build_context_scopes_api_to_inbound_agentic_identity(self, activity_processor):
        """Inbound Agent ID activities scope ctx.api with the inbound agentic identity."""
        core_activity = CoreActivity(
            type="message",
            id="activity-agentic",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {
                    "id": "bot-1",
                    "name": "Test Bot",
                    "agenticAppId": "agentic-app-id",
                    "agenticUserId": "agentic-user-id",
                    "tenantId": "tenant-id",
                },
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)
        mock_api_client = MagicMock()
        mock_api_client.users.token.get = AsyncMock(side_effect=Exception("no token"))

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        with patch("microsoft_teams.apps.app_process.ApiClient", return_value=mock_api_client) as mock_api_client_type:
            await activity_processor.process_activity([], mock_activity_event)

        assert mock_api_client_type.call_args.kwargs["auth_provider"] is activity_processor.auth_provider
        agentic_identity = mock_api_client_type.call_args.kwargs["agentic_identity"]
        assert agentic_identity.agentic_app_id == "agentic-app-id"
        assert agentic_identity.agentic_user_id == "agentic-user-id"
        assert agentic_identity.tenant_id == "tenant-id"

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
