"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
import json
import warnings
from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import AsyncMock, MagicMock, create_autospec, patch

import httpx
import pytest
from microsoft_teams.api import (
    Account,
    Activity,
    ActivityTypeAdapter,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    InvokeResponse,
    MessageActivityInput,
    PlanInfoEntity,
    SentActivity,
    Step,
    TokenProtocol,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC, US_GOV
from microsoft_teams.apps import ActivityContext, ActivityEvent, ActivitySentEvent, App, HttpStream, Plan
from microsoft_teams.apps.app_events import EventManager
from microsoft_teams.apps.app_process import ActivityProcessor
from microsoft_teams.apps.events import CoreActivity
from microsoft_teams.apps.plugins import PluginBase, StreamCancelledError
from microsoft_teams.apps.plugins.streamer import PlanConflictStreamError
from microsoft_teams.apps.routing.router import ActivityHandler, ActivityRouter
from microsoft_teams.apps.state import TurnState, TurnStateContainer, TurnStateLoader, TurnStateSealedError
from microsoft_teams.apps.token_provider import AppTokenProvider
from microsoft_teams.common import Client, EventEmitter, LocalStorage
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
        self.baggage_at_start: list[dict[str, object | None]] = []

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Iterator[RecordingSpan]:
        self.baggage_at_start.append(
            {
                "tenant_id": baggage.get_baggage("microsoft.tenant.id"),
                "conversation_id": baggage.get_baggage("gen_ai.conversation.id"),
            }
        )
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
        mock_token_provider = MagicMock(spec=AppTokenProvider)
        mock_get_app_graph_token = create_autospec(App, instance=True, spec_set=True)._get_graph_token
        mock_get_app_graph_token.return_value = None
        mock_get_agentic_graph_token = create_autospec(App, instance=True, spec_set=True)._get_agentic_graph_token
        mock_get_agentic_graph_token.return_value = None
        return ActivityProcessor(
            mock_activity_router,
            "id",
            mock_storage,
            "default_connection",
            mock_http_client,
            mock_token_provider,
            mock_get_app_graph_token,
            mock_get_agentic_graph_token,
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
    async def test_process_activity_applies_default_agent365_baggage_before_turn_span(self, activity_processor):
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
                    "agenticUserId": "agentic-user-1",
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
            assert baggage.get_baggage("user.name") is None
            assert baggage.get_baggage("user.email") is None
            assert baggage.get_baggage("gen_ai.agent.id") == "agent-app-1"
            assert baggage.get_baggage("gen_ai.agent.name") is None
            assert baggage.get_baggage("microsoft.agent.user.id") == "agentic-user-1"
            assert baggage.get_baggage("microsoft.agent.user.email") is None
            assert baggage.get_baggage("gen_ai.agent.description") is None
            assert baggage.get_baggage("microsoft.a365.agent.blueprint.id") == "blueprint-1"
            return InvokeResponse[Any](status=200)

        activity_processor._process_activity_core = AsyncMock(side_effect=process_core)
        tracer = RecordingTracer()

        with patch("microsoft_teams.apps.app_process.get_tracer", return_value=tracer):
            await activity_processor.process_activity([], mock_activity_event)

        assert tracer.baggage_at_start == [{"tenant_id": "tenant-1", "conversation_id": "conv-789"}]
        assert baggage.get_baggage("microsoft.tenant.id") is None
        assert baggage.get_baggage("gen_ai.agent.id") is None

    @pytest.mark.asyncio
    async def test_process_activity_can_disable_agent365_baggage(self, activity_processor):
        core_activity = CoreActivity(
            type="message",
            id="activity-disabled-baggage",
            service_url="https://service.url",
            **{
                "from": {"id": "user-123"},
                "conversation": {"id": "conv-789"},
                "recipient": {"id": "bot-456", "tenantId": "tenant-1"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        event = ActivityEvent(body=core_activity, token=mock_token)
        activity_processor.agent365_baggage_options = False

        async def process_core(plugins, event, activity):
            assert baggage.get_baggage("microsoft.tenant.id") is None
            return InvokeResponse[Any](status=200)

        activity_processor._process_activity_core = AsyncMock(side_effect=process_core)
        await activity_processor.process_activity([], event)

    @pytest.mark.asyncio
    async def test_process_activity_applies_configured_agent365_options(self, activity_processor):
        core_activity = CoreActivity(
            type="message",
            id="activity-configured-baggage",
            service_url="https://service.url",
            **{
                "from": {"id": "user-123", "name": "Caller"},
                "conversation": {"id": "conv-789"},
                "recipient": {"id": "bot-456", "tenantId": "tenant-1", "name": "Agent"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        event = ActivityEvent(body=core_activity, token=mock_token)
        activity_processor.agent365_baggage_options = {
            "include": ["senderName"],
            "operation_source": "Microsoft.Teams.Apps",
            "channel_link": "https://teams.microsoft.com/l/channel/channel-id",
            "additional_baggage": {"custom.key": "custom"},
        }

        async def process_core(plugins, event, activity):
            assert baggage.get_baggage("user.name") == "Caller"
            assert baggage.get_baggage("gen_ai.agent.name") is None
            assert baggage.get_baggage("service.name") == "Microsoft.Teams.Apps"
            assert baggage.get_baggage("microsoft.channel.link") == ("https://teams.microsoft.com/l/channel/channel-id")
            assert baggage.get_baggage("custom.key") == "custom"
            return InvokeResponse[Any](status=200)

        activity_processor._process_activity_core = AsyncMock(side_effect=process_core)
        await activity_processor.process_activity([], event)

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
        activity_processor.event_manager.on_activity_response.assert_awaited_once()
        response_event = activity_processor.event_manager.on_activity_response.await_args.args[0]
        assert response_event.response.status == expected_result.status
        assert response_event.response.body == expected_result.body

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
    @pytest.mark.parametrize(
        ("activity_id", "channel_data", "conversation", "expect_reply_chain", "destination"),
        [
            (
                "reply-2",
                {"chat": {"id": "19:user_bot@unq.gbl.spaces"}, "replyChain": {"id": "root-1"}},
                {"id": "a:encrypted"},
                True,
                "19:user_bot@unq.gbl.spaces",
            ),
            (
                "root-1",
                {"chat": {"id": "19:user_bot@unq.gbl.spaces"}, "replyChain": {"id": "root-1"}},
                {"id": "a:encrypted"},
                False,
                None,
            ),
            (
                "reply-2",
                {"channel": {"id": "19:channel@thread.tacv2"}, "replyChain": {"id": "root-1"}},
                {"id": "19:channel@thread.tacv2;messageid=root-1", "conversationType": "channel"},
                True,
                "19:channel@thread.tacv2",
            ),
        ],
        ids=["chat-in-thread", "chat-top-level", "channel"],
    )
    async def test_send_from_a_handler_is_placed_from_the_payload(
        self, activity_processor, activity_id, channel_data, conversation, expect_reply_chain, destination
    ):
        """The full pipeline places a reactive send in the reply chain named by the inbound payload."""
        from microsoft_teams.api import MessageActivityInput, SentActivity

        core_activity = CoreActivity(
            type="message",
            id=activity_id,
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": conversation,
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
                "channelData": channel_data,
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        mock_activity_event = ActivityEvent(body=core_activity, token=mock_token)

        sent = SentActivity(id="sent-1", activity_params=MessageActivityInput(text="hi"))
        activity_processor.http_client.clone.return_value = activity_processor.http_client
        with patch("microsoft_teams.apps.app_process.ApiClient") as mock_api_client:
            mock_context_api = MagicMock()
            mock_context_api.users.token.get = AsyncMock(side_effect=Exception("no token"))
            mock_context_api.conversations.create_activity = AsyncMock(return_value=sent)
            mock_context_api.conversations._create_reply_chain_activity = AsyncMock(return_value=sent)
            mock_context_api.clone.return_value = mock_context_api
            mock_api_client.return_value = mock_context_api

            async def calling_handler(ctx):
                await ctx.send("hi")
                return None

            activity_processor.router.select_handlers = MagicMock(return_value=[calling_handler])
            activity_processor.event_manager = MagicMock()
            activity_processor.event_manager.on_activity_response = AsyncMock()
            activity_processor.event_manager.on_activity_sent = AsyncMock()
            activity_processor.event_manager.on_error = AsyncMock()

            with warnings.catch_warnings():
                warnings.simplefilter("error", DeprecationWarning)
                await activity_processor.process_activity([], mock_activity_event)

        conversations = mock_context_api.conversations
        if expect_reply_chain:
            conversations._create_reply_chain_activity.assert_called_once()
            assert conversations._create_reply_chain_activity.call_args.args[:2] == (destination, "root-1")
            conversations.create_activity.assert_not_called()
        else:
            conversations.create_activity.assert_called_once()
            assert conversations.create_activity.call_args.args[0] == "a:encrypted"
            conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_updated_send_warns_once_when_given_a_conversation_ref(self, activity_processor):
        """ctx.send with a conversation reference is deprecated, and the warning is raised by the wrapper only once."""
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

        sent = SentActivity(id="sent-1", activity_params=MessageActivityInput(text="hi"))
        other_ref = ConversationReference(
            bot=Account(id="bot-1"),
            conversation=ConversationAccount(id="other-conv"),
            channel_id="msteams",
            service_url="https://service.url",
        )
        activity_processor.http_client.clone.return_value = activity_processor.http_client
        with patch("microsoft_teams.apps.app_process.ApiClient") as mock_api_client:
            mock_context_api = MagicMock()
            mock_context_api.users.token.get = AsyncMock(side_effect=Exception("no token"))
            mock_context_api.conversations.create_activity = AsyncMock(return_value=sent)
            mock_context_api.clone.return_value = mock_context_api
            mock_api_client.return_value = mock_context_api

            async def calling_handler(ctx):
                await ctx.send("hi", other_ref)
                return None

            activity_processor.router.select_handlers = MagicMock(return_value=[calling_handler])
            activity_processor.event_manager = MagicMock()
            activity_processor.event_manager.on_activity_response = AsyncMock()
            activity_processor.event_manager.on_activity_sent = AsyncMock()
            activity_processor.event_manager.on_error = AsyncMock()

            with pytest.warns(DeprecationWarning, match="to send to a different conversation") as recorded:
                await activity_processor.process_activity([], mock_activity_event)

        deprecations = [w for w in recorded if issubclass(w.category, DeprecationWarning)]
        assert len(deprecations) == 1
        assert mock_context_api.conversations.create_activity.call_args.args[0] == "other-conv"
        sent_event = activity_processor.event_manager.on_activity_sent.call_args.args[0]
        assert sent_event.conversation_ref == other_ref

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

    @pytest.fixture
    async def plan_context(self, activity_processor):
        activity_processor.fetch_user_token = False
        token = MagicMock(spec=TokenProtocol)
        token.service_url = "https://service.url"
        api = MagicMock(spec=ApiClient)
        api.from_service_url.return_value = api
        api.conversations = MagicMock()

        async def create_activity(conversation_id, activity):
            activity_id = "answer" if isinstance(activity, MessageActivityInput) else "DO_NOT_USE_PLACEHOLDER_ID"
            return SentActivity(id=activity_id, activity_params=activity)

        api.conversations.create_activity = AsyncMock(side_effect=create_activity)
        events = EventEmitter[str]()
        sent = asyncio.Queue[ActivitySentEvent]()
        events.on("activity_sent", sent.put_nowait)
        activity_processor.event_manager = EventManager(events)
        plugin = MagicMock(spec=PluginBase)
        with patch("microsoft_teams.apps.app_process.ApiClient", return_value=api):
            context = await activity_processor._build_context(_message_activity("inbound-id"), token, [plugin])
            yield context, api, plugin, sent, token

    @pytest.mark.parametrize(
        "method,operation",
        [
            ("start", "start"),
            ("update", "continue"),
            ("stop", "stop"),
            ("error", "error"),
            ("complete", "complete"),
        ],
    )
    async def test_context_plan_notifies_app_and_plugin_once(self, plan_context, method, operation):
        ctx, api, plugin, sent, _ = plan_context
        plan = ctx.plan()
        if method == "complete":
            result = await plan.complete("Done")
        elif method in ("start", "update"):
            result = await getattr(plan, method)([Step(id="lookup", version=1, title="Lookup", status="active")])
        else:
            result = await getattr(plan, method)()

        event = await asyncio.wait_for(sent.get(), timeout=1)

        assert sent.empty()
        api.conversations.create_activity.assert_awaited_once()
        plugin.on_activity_sent.assert_awaited_once()
        plugin_event = plugin.on_activity_sent.call_args.args[0]
        assert plugin_event.activity is event.activity
        assert plugin_event.conversation_ref == event.conversation_ref
        assert event.conversation_ref == ctx.conversation_ref
        assert event.conversation_ref.activity_id == "inbound-id"
        activity = event.activity.activity_params
        assert activity.reply_to_id == "inbound-id"
        assert activity.entities[0].plan_type == operation
        if operation == "complete":
            assert event.activity is result
            assert event.activity.id == "answer"
            assert activity.type == "message"
        else:
            assert result is None
            assert event.activity.id == "DO_NOT_USE_PLACEHOLDER_ID"
            assert activity.type == "typing"

    async def test_context_plan_rejects_prompt_override(self, plan_context):
        ctx, api, plugin, sent, _ = plan_context

        with pytest.raises(TypeError, match="reply_to_id"):
            ctx.plan(reply_to_id="other-prompt")  # pyright: ignore[reportCallIssue]

        api.conversations.create_activity.assert_not_awaited()
        plugin.on_activity_sent.assert_not_awaited()
        assert sent.empty()

    async def test_context_plan_subscribes_once_without_replacing_listeners(self, plan_context):
        ctx, _, plugin, sent, _ = plan_context
        plan = ctx.plan()
        on_sent = MagicMock()
        plan.events.on("sent", on_sent)
        assert ctx.plan() is plan
        assert ctx.plan() is plan
        assert plan.events.listener_count("sent") == 2
        expected_ref = ctx.conversation_ref.model_copy(deep=True)
        ctx.conversation_ref = ctx.conversation_ref.model_copy(deep=True)
        ctx.conversation_ref.conversation.id = "changed-chat"

        await plan.start([Step(id="lookup", version=1, title="Lookup", status="active")])
        await ctx.plan().complete("Done")
        received = [await asyncio.wait_for(sent.get(), timeout=1) for _ in range(2)]

        assert sent.empty()
        assert plugin.on_activity_sent.await_count == 2
        assert [event.activity.activity_params.reply_to_id for event in received] == [
            "inbound-id",
            "inbound-id",
        ]
        assert all(event.conversation_ref == expected_ref for event in received)
        assert on_sent.call_count == 2
        assert on_sent.call_args_list[0].args[0] is received[0].activity
        assert on_sent.call_args_list[1].args[0] is received[1].activity

    async def test_plan_notifications_do_not_use_context_send_or_targeting(self, plan_context):
        ctx, api, _, sent, _ = plan_context
        ctx.activity.recipient.is_targeted = True
        ctx.send = AsyncMock()

        result = await ctx.plan().complete("Done")
        event = await asyncio.wait_for(sent.get(), timeout=1)

        ctx.send.assert_not_awaited()
        api.conversations.create_activity.assert_awaited_once()
        api.conversations.create_targeted_activity.assert_not_called()
        assert result.activity_params.recipient is None
        assert event.activity is result
        assert sent.empty()

    async def test_plan_event_reference_is_independent_for_each_send(self, plan_context):
        ctx, _, _, sent, _ = plan_context
        plan = ctx.plan()
        expected_ref = ctx.conversation_ref.model_copy(deep=True)

        await plan.start([Step(id="lookup", version=1, title="Lookup", status="active")])
        first = await asyncio.wait_for(sent.get(), timeout=1)
        first.conversation_ref.bot.id = "changed-by-listener"
        first.conversation_ref.conversation.id = "changed-chat"

        await plan.complete("Done")
        second = await asyncio.wait_for(sent.get(), timeout=1)

        assert second.conversation_ref == expected_ref
        assert second.conversation_ref is not first.conversation_ref
        assert second.activity.activity_params.from_ is None
        assert second.activity.activity_params.conversation.model_dump(exclude_none=True) == {
            "id": expected_ref.conversation.id
        }

    @pytest.mark.parametrize("method", ["start", "complete"])
    async def test_failed_context_plan_does_not_notify_app_or_plugin(self, plan_context, method):
        ctx, api, plugin, sent, _ = plan_context
        plan = ctx.plan()
        on_sent = MagicMock()
        plan.events.on("sent", on_sent)
        api.conversations.create_activity.side_effect = RuntimeError("Plan send failed")

        with pytest.raises(RuntimeError, match="Plan send failed"):
            if method == "start":
                await plan.start([Step(id="lookup", version=1, title="Lookup", status="active")])
            else:
                await plan.complete("Done")

        on_sent.assert_not_called()
        plugin.on_activity_sent.assert_not_awaited()
        assert sent.empty()

    async def test_retained_context_plan_notifies_after_turn(self, activity_processor, plan_context):
        ctx, api, plugin, sent, token = plan_context
        saved: list[Plan] = []

        async def retain_plan(context):
            saved.append(context.plan())

        activity_processor.router.select_handlers.return_value = [retain_plan]
        response = await activity_processor.process_activity(
            [plugin],
            ActivityEvent(body=CoreActivity.model_validate(ctx.activity.model_dump()), token=token),
        )
        assert response.status == 200
        api.conversations.create_activity.assert_not_awaited()
        assert sent.empty()

        result = await saved[0].complete("Background answer")
        event = await asyncio.wait_for(sent.get(), timeout=1)

        assert event.activity is result
        assert event.activity.activity_params.reply_to_id == "inbound-id"
        plugin.on_activity_sent.assert_awaited_once()
        assert sent.empty()

    async def test_caught_final_plan_conflict_does_not_fail_processor_cleanup(self, activity_processor):
        requests = []
        rejections = []
        caught = []
        error_body = {"error": {"code": "PlanConflict", "message": "The user stopped this plan."}}

        def handle(request):
            payload = json.loads(request.content)
            requests.append((request, payload))
            assert request.method == "POST"
            assert request.url.host == "service.url"
            assert request.url.path == "/v3/conversations/conv-789/activities"
            operations = [entity["planType"] for entity in payload.get("entities", []) if entity["type"] == "planInfo"]
            if operations == ["complete"]:
                response = httpx.Response(409, json=error_body)
                rejections.append(response)
                return response
            if operations == ["stop"]:
                return httpx.Response(202)
            assert not operations
            assert payload["type"] == "typing"
            return httpx.Response(201, json={"id": "stream-id"})

        events = EventEmitter[str]()
        sent = asyncio.Queue[ActivitySentEvent]()
        on_error = MagicMock()
        on_response = MagicMock()
        on_close = MagicMock()
        events.on("activity_sent", sent.put_nowait)
        events.on("error", on_error)
        events.on("activity_response", on_response)
        activity_processor.event_manager = EventManager(events)
        activity_processor.fetch_user_token = False
        activity_processor.token_provider.get_app_token.return_value = None

        async def handler(ctx):
            assert isinstance(ctx, ActivityContext)
            assert isinstance(ctx.stream, HttpStream)
            ctx.stream.on_close(on_close)
            plan = ctx.plan()
            ctx.stream.emit("Final answer")
            ctx.stream.emit(plan.completion())
            try:
                await ctx.stream.close()
            except PlanConflictStreamError as error:
                caught.append(error)
                await plan.stop()
            else:
                pytest.fail("The transport must reject every Plan completion")

        activity_processor.router = ActivityRouter()
        activity_processor.router.add_handler(lambda activity: activity.type == "message", handler)
        token = MagicMock(spec=TokenProtocol)
        token.service_url = "https://service.url"
        event = ActivityEvent(body=CoreActivity.model_validate(_message_activity().model_dump()), token=token)
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
            activity_processor.http_client = Client(_http=http)
            response = await activity_processor.process_activity([], event)
            received = [await asyncio.wait_for(sent.get(), timeout=1) for _ in range(2)]

        assert response.status == 200
        on_error.assert_not_called()
        on_close.assert_not_called()
        on_response.assert_called_once()
        assert sent.empty()
        assert len(requests) == 3
        assert [payload["type"] for _, payload in requests] == ["typing", "message", "typing"]
        assert all(payload["replyToId"] == "activity-123" for _, payload in requests)
        assert len(rejections) == len(caught) == 1
        error = caught[0]
        assert error.response is rejections[0]
        assert error.response.status_code == 409
        assert error.response.json() == error_body
        assert error.request is requests[1][0]
        assert isinstance(error.__cause__, httpx.HTTPStatusError)
        assert error.__cause__.response is error.response
        assert error.__cause__.request is error.request
        assert str(error) == str(error.__cause__)
        assert all(event.activity.activity_params.type == "typing" for event in received)
        assert received[-1].activity.activity_params.entities == [PlanInfoEntity(plan_type="stop")]
        assert received[-1].activity.id == "DO_NOT_USE_PLACEHOLDER_ID"

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
        """Inbound Agent ID activities scope ctx.api with the inbound agentic user."""
        core_activity = CoreActivity(
            type="message",
            id="activity-agentic-user",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {
                    "id": "bot-1",
                    "name": "Test Bot",
                    "agenticAppId": "agentic-app-id",
                    "agenticUserId": "agentic-user-id",
                    "agenticAppBlueprintId": "blueprint-id",
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

        assert mock_api_client_type.call_args.kwargs["token_provider"] is activity_processor.token_provider
        assert mock_api_client_type.call_args.kwargs["cloud"] is activity_processor.cloud
        agentic_identity = mock_api_client_type.call_args.kwargs["agentic_identity"]
        assert agentic_identity.agentic_app_id == "agentic-app-id"
        assert agentic_identity.agentic_user_id == "agentic-user-id"
        assert agentic_identity.agentic_app_blueprint_id == "blueprint-id"
        assert agentic_identity.tenant_id == "tenant-id"

    @pytest.mark.asyncio
    async def test_build_context_defers_graph_tenant_resolution(self, activity_processor):
        activity_processor.fetch_user_token = False
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"

        context = await activity_processor._build_context(_message_activity("activity-graph-tenant"), mock_token, [])
        await context._app_token()

        activity_processor.get_app_graph_token.assert_awaited_once_with(None)

    @pytest.mark.asyncio
    async def test_build_context_passes_sovereign_cloud_to_api_client(self, activity_processor):
        activity_processor.fetch_user_token = False
        activity_processor.cloud = US_GOV
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"

        with patch("microsoft_teams.apps.app_process.ApiClient") as mock_api_client_type:
            await activity_processor._build_context(_message_activity("activity-sovereign-cloud"), mock_token, [])

        assert mock_api_client_type.call_args.kwargs["cloud"] is US_GOV

    @pytest.mark.asyncio
    async def test_build_context_gives_ctx_files_an_agentic_credential(self, activity_processor):
        """
        An inbound Agentic User activity must reach `ctx.files` as an agentic credential.

        This asserts the seam, not the parts. `select_files_credential` and `FilesAccessor` are both covered on their
        own, and both stayed green through a revision where nothing connected them, so `ctx.files` held no credential
        and every Graph path was unreachable in production.
        """
        activity_processor.fetch_user_token = False
        activity_processor.http_client.http = MagicMock()
        core_activity = CoreActivity(
            type="message",
            id="activity-files-credential",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {
                    "id": "bot-1",
                    "name": "Test Bot",
                    "agenticAppId": "agentic-app-id",
                    "agenticUserId": "agentic-user-id",
                    "agenticAppBlueprintId": "blueprint-id",
                    "tenantId": "tenant-id",
                },
                "channelId": "msteams",
            },
        )
        activity = ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"

        context = await activity_processor._build_context(activity, mock_token, [])
        credential = context.files._credential

        assert credential is not None
        assert credential.actor == "agentic_user"

        await credential.token()
        activity_processor.get_agentic_graph_token.assert_awaited_once()
        assert activity_processor.get_agentic_graph_token.await_args.args[0].agentic_user_id == "agentic-user-id"

    @pytest.mark.asyncio
    async def test_build_context_gives_ctx_files_the_activitys_tenant(self, activity_processor):
        """
        The app credential behind `ctx.files` must ask for the activity's own tenant, not a default.

        Uses an activity whose tenant arrives only on channel data, so this pins the whole chain: the extraction
        fallback, the closure that carries the tenant into the credential, and the token call itself. A single-tenant
        bot that asked for the wrong tenant here would read files as the wrong directory.
        """
        activity_processor.fetch_user_token = False
        activity_processor.http_client.http = MagicMock()
        core_activity = CoreActivity(
            type="message",
            id="activity-files-tenant",
            service_url="https://service.url",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
                "channelData": {"tenant": {"id": "tenant-from-channel-data"}},
            },
        )
        activity = ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"

        context = await activity_processor._build_context(activity, mock_token, [])
        credential = context.files._credential

        assert credential is not None
        assert credential.actor == "app"

        await credential.token()
        activity_processor.get_app_graph_token.assert_any_await("tenant-from-channel-data")

    @pytest.mark.asyncio
    async def test_build_context_gives_ctx_files_an_app_credential_without_agentic_identity(self, activity_processor):
        """A traditional bot still gets a credential, so the expiry fallback has a token to resolve."""
        activity_processor.fetch_user_token = False
        activity_processor.http_client.http = MagicMock()
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"

        context = await activity_processor._build_context(_message_activity("activity-app-credential"), mock_token, [])
        credential = context.files._credential

        assert credential is not None
        assert credential.actor == "app"

    @pytest.mark.asyncio
    async def test_build_context_reads_inline_images_with_the_token_of_the_turns_own_api_client(
        self, activity_processor
    ):
        """An inbound Agentic User activity must reach `ctx.files` as an agentic Bot API credential."""
        activity_processor.fetch_user_token = False
        activity_processor.http_client.http = MagicMock()
        core_activity = CoreActivity(
            type="message",
            id="activity-inline-credential",
            service_url="https://service.url/",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {
                    "id": "bot-1",
                    "name": "Test Bot",
                    "agenticAppId": "agentic-app-id",
                    "agenticUserId": "agentic-user-id",
                    "agenticAppBlueprintId": "blueprint-id",
                    "tenantId": "tenant-id",
                },
                "channelId": "msteams",
            },
        )
        activity = ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url/"

        context = await activity_processor._build_context(activity, mock_token, [])
        credential = context.files._bot_api_credential

        assert credential is not None
        assert credential.actor == "agentic_user"

        # The client's token is scoped to the inbound identity, so an agentic identity reads as itself.
        context.api.http.token = "turn-client-token"
        assert await credential.token() == "turn-client-token"

    @pytest.mark.asyncio
    async def test_build_context_resolves_the_turn_clients_token_factory_and_carries_the_service_url(
        self, activity_processor
    ):
        """The credential reads the API client's token source at fetch time, factory shape included."""
        activity_processor.fetch_user_token = False
        activity_processor.http_client.http = MagicMock()
        core_activity = CoreActivity(
            type="message",
            id="activity-inline-factory",
            service_url="https://service.url/amer/",
            **{
                "from": {"id": "user-1", "name": "Test User"},
                "conversation": {"id": "conv-1"},
                "recipient": {"id": "bot-1", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        activity = ActivityTypeAdapter.validate_python(core_activity.model_dump(by_alias=True, exclude_none=True))
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url/amer/"

        context = await activity_processor._build_context(activity, mock_token, [])
        credential = context.files._bot_api_credential

        assert credential is not None
        assert credential.actor == "app"
        assert credential.service_url == "https://service.url/amer/"

        calls: list[int] = []

        async def factory() -> str:
            calls.append(1)
            return "factory-token"

        context.api.http.token = factory
        assert await credential.token() == "factory-token"
        assert calls == [1]

    @pytest.mark.asyncio
    async def test_build_context_skips_token_fetch_when_disabled(self, activity_processor):
        """When fetch_user_token is False, the user-token API is not called."""
        from unittest.mock import patch

        activity_processor.fetch_user_token = False

        core_activity = CoreActivity(
            type="message",
            id="activity-no-token",
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

        mock_api_client = MagicMock()
        mock_api_client.users.get_token = AsyncMock()

        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

        with patch("microsoft_teams.apps.app_process.ApiClient", return_value=mock_api_client):
            await activity_processor.process_activity([], mock_activity_event)

        mock_api_client.users.get_token.assert_not_called()

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
    async def test_process_activity_stream_cancelled_raises_state_save_failure(self, activity_processor):
        """A handled stream cancellation does not hide a persistence failure."""
        save_error = RuntimeError("save failed")
        container = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="conv-789",
        )

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(return_value=container)
        activity_processor.state_loader.save = AsyncMock(side_effect=save_error)
        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.execute_middleware_chain = AsyncMock(side_effect=StreamCancelledError())
        self._wire_event_manager(activity_processor)

        with pytest.raises(RuntimeError) as exc_info:
            await activity_processor.process_activity([], self._message_event())

        assert exc_info.value is save_error
        error_event = activity_processor.event_manager.on_error.await_args.args[0]
        assert error_event.error is save_error
        activity_processor.event_manager.on_activity_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_process_activity_handles_response_event_stream_cancelled(self, activity_processor):
        """StreamCancelledError from the response event retains the legacy 200 response."""
        core_activity = CoreActivity(
            type="message",
            id="activity-response-cancel",
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
        activity_processor.execute_middleware_chain = AsyncMock(
            return_value=InvokeResponse(status=202, body={"accepted": True})
        )
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock(side_effect=StreamCancelledError())
        activity_processor.event_manager.on_error = AsyncMock()

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as mock_stream_class:
            mock_stream = mock_stream_class.return_value
            mock_stream.close = AsyncMock()

            result = await activity_processor.process_activity([], mock_activity_event)

        assert result.status == 200
        assert mock_stream.close.await_count == 2

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

    @pytest.mark.asyncio
    async def test_state_load_failure_emits_error_event(self, activity_processor):
        """State load failures are handled by the same on_error path as handler failures."""
        mock_plugins = []
        mock_activity_event = self._message_event("activity-load-failure")
        load_error = RuntimeError("storage unavailable")

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(side_effect=load_error)
        activity_processor.state_loader.save = AsyncMock()
        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.execute_middleware_chain = AsyncMock()
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_error = AsyncMock()

        with pytest.raises(RuntimeError, match="storage unavailable"):
            await activity_processor.process_activity(mock_plugins, mock_activity_event)

        activity_processor.event_manager.on_error.assert_called_once()
        activity_processor.execute_middleware_chain.assert_not_called()

    # --- Per-turn state (App(state=...)) integration -----------------------

    @staticmethod
    def _message_event(activity_id: str = "activity-state", user_id: str = "user-123") -> ActivityEvent:
        core_activity = CoreActivity(
            type="message",
            id=activity_id,
            service_url="https://service.url",
            **{
                "from": {"id": user_id, "name": "Test User"},
                "conversation": {"id": "conv-789"},
                "recipient": {"id": "bot-456", "name": "Test Bot"},
                "channelId": "msteams",
            },
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_token.service_url = "https://service.url"
        return ActivityEvent(body=core_activity, token=mock_token)

    def _wire_event_manager(self, activity_processor):
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()
        activity_processor.event_manager.on_error = AsyncMock()

    @pytest.mark.asyncio
    async def test_state_disabled_leaves_ctx_state_none(self, activity_processor):
        """With no state loader, ctx.state is None for handlers."""
        captured: dict[str, Any] = {}

        async def handler(ctx: ActivityContext[Activity]) -> None:
            captured["state"] = ctx.state

        activity_processor.state_loader = None
        activity_processor.router.select_handlers = MagicMock(return_value=[handler])
        self._wire_event_manager(activity_processor)

        await activity_processor.process_activity([], self._message_event())

        assert captured["state"] is None

    @pytest.mark.asyncio
    async def test_state_enabled_exposes_scopes_and_persists_across_turns(self, activity_processor):
        """Handlers see loaded scopes, and writes persist to the next turn."""

        storage: LocalStorage[str] = LocalStorage()
        activity_processor.state_loader = TurnStateLoader(storage)
        self._wire_event_manager(activity_processor)

        async def writer(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is not None
            ctx.state.conversation["greeted"] = True
            assert ctx.state.user is not None
            ctx.state.user["count"] = 1

        activity_processor.router.select_handlers = MagicMock(return_value=[writer])
        await activity_processor.process_activity([], self._message_event("turn-1"))

        seen: dict[str, Any] = {}

        async def reader(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is not None and ctx.state.user is not None
            seen["greeted"] = ctx.state.conversation.get("greeted")
            seen["count"] = ctx.state.user.get("count")

        activity_processor.router.select_handlers = MagicMock(return_value=[reader])
        await activity_processor.process_activity([], self._message_event("turn-2"))

        assert seen == {"greeted": True, "count": 1}

    @pytest.mark.asyncio
    async def test_state_empty_sender_id_persists_conversation_without_user_scope(self, activity_processor):
        """An empty sender ID omits user state without blocking conversation persistence."""
        storage: LocalStorage[str] = LocalStorage()
        activity_processor.state_loader = TurnStateLoader(storage)
        self._wire_event_manager(activity_processor)
        holder: dict[str, TurnStateContainer] = {}

        async def handler(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is not None
            holder["state"] = ctx.state
            assert ctx.state.user is None
            ctx.state.conversation["value"] = "saved"

        activity_processor.router.select_handlers = MagicMock(return_value=[handler])

        response = await activity_processor.process_activity([], self._message_event(user_id=""))

        assert response.status == 200
        assert holder["state"].user is None
        reloaded = await TurnStateLoader(storage).load("conv-789")
        assert reloaded.conversation["value"] == "saved"

    @pytest.mark.asyncio
    async def test_state_is_sealed_after_turn(self, activity_processor):
        """State is sealed once the turn ends; later access raises."""

        storage: LocalStorage[str] = LocalStorage()
        activity_processor.state_loader = TurnStateLoader(storage)
        self._wire_event_manager(activity_processor)

        holder: dict[str, Any] = {}

        async def handler(ctx: ActivityContext[Activity]) -> None:
            holder["state"] = ctx.state

        activity_processor.router.select_handlers = MagicMock(return_value=[handler])
        await activity_processor.process_activity([], self._message_event())

        with pytest.raises(TurnStateSealedError):
            _ = holder["state"].conversation["greeted"]

    @pytest.mark.asyncio
    async def test_state_saved_even_when_handler_raises(self, activity_processor):
        """Dirty state is persisted in the finally even if the handler throws."""

        storage: LocalStorage[str] = LocalStorage()
        activity_processor.state_loader = TurnStateLoader(storage)
        self._wire_event_manager(activity_processor)

        async def boom(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is not None
            ctx.state.conversation["partial"] = True
            raise RuntimeError("boom")

        activity_processor.router.select_handlers = MagicMock(return_value=[boom])

        with pytest.raises(RuntimeError, match="boom"):
            await activity_processor.process_activity([], self._message_event())

        reloaded = await TurnStateLoader(storage).load("conv-789", "user-123")
        assert reloaded.conversation["partial"] is True

    @pytest.mark.asyncio
    async def test_state_is_sealed_when_save_raises(self, activity_processor):
        """State is sealed even when persistence fails."""
        save_error = RuntimeError("save failed")
        container = TurnStateContainer(
            conversation=TurnState({"value": "dirty"}),
            conversation_id="conv-789",
            user=TurnState({"value": "dirty"}),
            user_id="user-123",
        )
        container.conversation["value"] = "changed"

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(return_value=container)
        activity_processor.state_loader.save = AsyncMock(side_effect=save_error)
        self._wire_event_manager(activity_processor)
        activity_processor.router.select_handlers = MagicMock(return_value=[])

        with pytest.raises(RuntimeError, match="save failed"):
            await activity_processor.process_activity([], self._message_event())

        assert container.conversation.is_sealed is True
        assert container.user is not None and container.user.is_sealed is True
        error_event = activity_processor.event_manager.on_error.await_args.args[0]
        assert error_event.error is save_error
        activity_processor.event_manager.on_activity_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_state_save_failure_raised_inside_unrelated_exception_handler(self, activity_processor):
        """A caller's handled exception does not hide a persistence failure."""
        save_error = RuntimeError("save failed")
        container = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="conv-789",
        )

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(return_value=container)
        activity_processor.state_loader.save = AsyncMock(side_effect=save_error)
        self._wire_event_manager(activity_processor)
        activity_processor.router.select_handlers = MagicMock(return_value=[])

        try:
            raise ValueError("unrelated caller error")
        except ValueError:
            with pytest.raises(RuntimeError) as exc_info:
                await activity_processor.process_activity([], self._message_event())

        assert exc_info.value is save_error
        error_event = activity_processor.event_manager.on_error.await_args.args[0]
        assert error_event.error is save_error
        activity_processor.event_manager.on_activity_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_state_save_failure_does_not_mask_handler_error(self, activity_processor):
        """A persistence failure is reported without replacing the handler failure."""
        handler_error = ValueError("handler failed")
        save_error = RuntimeError("save failed")
        reporting_error = RuntimeError("error reporter failed")
        container = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="conv-789",
        )

        async def handler(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is container
            ctx.state.conversation["value"] = "changed"
            raise handler_error

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(return_value=container)
        activity_processor.state_loader.save = AsyncMock(side_effect=save_error)
        self._wire_event_manager(activity_processor)
        activity_processor.event_manager.on_error.side_effect = [None, reporting_error]
        activity_processor.router.select_handlers = MagicMock(return_value=[handler])

        with pytest.raises(ValueError, match="handler failed") as exc_info:
            await activity_processor.process_activity([], self._message_event())

        assert exc_info.value is handler_error
        assert container.conversation.is_sealed is True
        errors = [call.args[0].error for call in activity_processor.event_manager.on_error.await_args_list]
        assert errors == [handler_error, save_error]
        activity_processor.event_manager.on_activity_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_state_save_failure_does_not_mask_handler_cancellation(self, activity_processor):
        """Handler cancellation remains authoritative when persistence also fails."""
        save_error = RuntimeError("save failed")
        container = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="conv-789",
        )

        async def handler(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is container
            ctx.state.conversation["value"] = "changed"
            raise asyncio.CancelledError()

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(return_value=container)
        activity_processor.state_loader.save = AsyncMock(side_effect=save_error)
        self._wire_event_manager(activity_processor)
        activity_processor.router.select_handlers = MagicMock(return_value=[handler])

        with pytest.raises(asyncio.CancelledError):
            await activity_processor.process_activity([], self._message_event())

        assert container.conversation.is_sealed is True
        error_event = activity_processor.event_manager.on_error.await_args.args[0]
        assert error_event.error is save_error
        activity_processor.event_manager.on_activity_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_task_cancellation_during_state_save_seals_state(self, activity_processor):
        """Cancellation during persistence propagates after sealing state."""
        container = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="conv-789",
        )
        save_started = asyncio.Event()
        block_save = asyncio.Event()

        async def save(_: TurnStateContainer) -> None:
            save_started.set()
            await block_save.wait()

        activity_processor.state_loader = MagicMock()
        activity_processor.state_loader.load = AsyncMock(return_value=container)
        activity_processor.state_loader.save = AsyncMock(side_effect=save)
        self._wire_event_manager(activity_processor)
        activity_processor.router.select_handlers = MagicMock(return_value=[])

        task = asyncio.create_task(activity_processor.process_activity([], self._message_event()))
        await save_started.wait()
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task

        assert container.conversation.is_sealed is True
        activity_processor.event_manager.on_activity_response.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_activity_response_failure_occurs_after_state_is_persisted(self, activity_processor):
        """Response-event failures are reported after state has been safely persisted."""
        response_error = RuntimeError("response event failed")
        storage: LocalStorage[str] = LocalStorage()
        activity_processor.state_loader = TurnStateLoader(storage)
        self._wire_event_manager(activity_processor)
        activity_processor.event_manager.on_activity_response.side_effect = response_error
        holder: dict[str, TurnStateContainer] = {}

        async def handler(ctx: ActivityContext[Activity]) -> None:
            assert ctx.state is not None
            holder["state"] = ctx.state
            ctx.state.conversation["value"] = "saved"

        activity_processor.router.select_handlers = MagicMock(return_value=[handler])

        with pytest.raises(RuntimeError, match="response event failed"):
            await activity_processor.process_activity([], self._message_event())

        assert holder["state"].conversation.is_sealed is True
        reloaded = await TurnStateLoader(storage).load("conv-789", "user-123")
        assert reloaded.conversation["value"] == "saved"
        error_event = activity_processor.event_manager.on_error.await_args.args[0]
        assert error_event.error is response_error
