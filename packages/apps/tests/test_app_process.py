"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.api import (
    Account,
    Activity,
    ActivityBase,
    ConversationAccount,
    ConversationReference,
    InvokeResponse,
    MessageActivity,
    TokenProtocol,
)
from microsoft.teams.apps import ActivityContext, Sender
from microsoft.teams.apps.app_events import EventManager
from microsoft.teams.apps.app_process import ActivityProcessor
from microsoft.teams.apps.events.types import ActivityEvent
from microsoft.teams.apps.routing.router import ActivityHandler, ActivityRouter
from microsoft.teams.apps.token_manager import TokenManager
from microsoft.teams.common import Client, LocalStorage
from typing_extensions import Any


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
    def activity_processor(self, mock_logger, mock_http_client):
        """Create an ActivityProcessor instance."""
        mock_storage = MagicMock(spec=LocalStorage)
        mock_activity_router = MagicMock(spec=ActivityRouter)
        mock_token_manager = MagicMock(spec=TokenManager)
        return ActivityProcessor(
            mock_activity_router,
            mock_logger,
            "id",
            mock_storage,
            "default_connection",
            mock_http_client,
            mock_token_manager,
            None,
        )

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_with_no_handlers(self, activity_processor):
        """Test the process_activity method with no handlers."""
        context = MagicMock(spec=ActivityContext)
        activity_processor.event_manager = MagicMock(spec=EventManager)

        response = await activity_processor.execute_middleware_chain(context, [])
        assert response is None

    @pytest.mark.asyncio
    async def test_execute_middleware_chain_with_two_handlers(self, activity_processor, mock_http_client, mock_logger):
        """Test the execute_middleware_chain method with two handlers."""
        context = ActivityContext(
            activity=MagicMock(spec=ActivityBase),
            app_id="app_id",
            logger=mock_logger,
            storage=MagicMock(spec=LocalStorage),
            api=mock_http_client,
            user_token=None,
            conversation_ref=MagicMock(spec=ConversationReference),
            is_signed_in=True,
            connection_name="default_connection",
            sender=MagicMock(spec=Sender),
            app_token=None,
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
        mock_sender = MagicMock()
        stream = MagicMock()
        stream.close = AsyncMock()
        mock_sender.create_stream.return_value = stream

        # Create real activity and event
        mock_account = Account(id="user-123", name="Test User")
        mock_conversation = ConversationAccount(id="conv-789")
        mock_bot = Account(id="bot-456", name="Test Bot")
        activity = MessageActivity(
            type="message",
            text="Test message",
            from_=mock_account,
            conversation=mock_conversation,
            recipient=mock_bot,
            id="activity-123",
            service_url="https://service.url",
        )
        mock_token = MagicMock(spec=TokenProtocol)
        mock_activity_event = ActivityEvent(activity=activity, sender=mock_sender, token=mock_token)

        # Setup processor mocks
        activity_processor.router.select_handlers = MagicMock(return_value=[])
        activity_processor.execute_middleware_chain = AsyncMock(return_value=middleware_result)
        activity_processor.event_manager = MagicMock()
        activity_processor.event_manager.on_activity_response = AsyncMock()

        # Act
        result = await activity_processor.process_activity(mock_plugins, mock_sender, mock_activity_event)

        # Assert
        assert result.status == expected_result.status
        assert result.body == expected_result.body
