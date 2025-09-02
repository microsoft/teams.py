"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.api import Activity, ActivityBase, ConversationReference
from microsoft.teams.apps import ActivityContext, AppTokens, Sender
from microsoft.teams.apps.app_events import EventManager
from microsoft.teams.apps.app_process import ActivityProcessor
from microsoft.teams.apps.graph_token_manager import GraphTokenManager
from microsoft.teams.apps.routing.router import ActivityHandler, ActivityRouter
from microsoft.teams.common import Client, ConsoleLogger, LocalStorage


class TestActivityProcessor:
    @pytest.fixture
    def mock_logger(self):
        return MagicMock(spec=ConsoleLogger)

    @pytest.fixture
    def mock_http_client(self):
        return MagicMock(spec=Client)

    @pytest.fixture
    def activity_processor(self, mock_logger, mock_http_client):
        """Create an ActivityProcessor instance."""
        mock_storage = MagicMock(spec=LocalStorage)
        mock_activity_router = MagicMock(spec=ActivityRouter)
        mock_tokens = MagicMock(spec=AppTokens)
        mock_graph_token_manager = MagicMock(spec=GraphTokenManager)
        return ActivityProcessor(
            mock_activity_router,
            mock_logger,
            "id",
            mock_storage,
            "default_connection",
            mock_http_client,
            mock_tokens,
            mock_graph_token_manager,
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
