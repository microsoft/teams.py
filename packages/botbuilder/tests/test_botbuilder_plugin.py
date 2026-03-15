# pyright: reportMissingTypeStubs=false
"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.integration.aiohttp import CloudAdapter
from botbuilder.schema import Activity
from microsoft_teams.api import Credentials
from microsoft_teams.apps.http import HttpRequest, HttpResponse
from microsoft_teams.apps.http.http_server import HttpServer
from microsoft_teams.botbuilder import BotBuilderPlugin


class TestBotBuilderPlugin:
    """Tests for BotBuilderPlugin."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def mock_http_server(self):
        server = MagicMock(spec=HttpServer)
        server.adapter = MagicMock()
        server.handle_request = AsyncMock(return_value=HttpResponse(status=200, body=None))
        return server

    @pytest.fixture
    def plugin_without_adapter(self, mock_http_server):
        plugin = BotBuilderPlugin()
        plugin.credentials = MagicMock(spec=Credentials)
        plugin.credentials.client_id = "abc"
        plugin.credentials.client_secret = "secret"
        plugin.credentials.tenant_id = "tenant-123"
        plugin.http_server = mock_http_server
        plugin.logger = MagicMock()
        return plugin

    @pytest.fixture
    def plugin_with_adapter(self, mock_http_server) -> BotBuilderPlugin:
        adapter = MagicMock(spec=CloudAdapter)
        plugin = BotBuilderPlugin(adapter=adapter)
        handler = AsyncMock(spec=ActivityHandler)
        plugin.handler = handler
        plugin.http_server = mock_http_server
        plugin.logger = MagicMock()
        return plugin

    @pytest.mark.asyncio
    async def test_on_init_creates_adapter_when_missing(self, plugin_without_adapter: BotBuilderPlugin):
        assert plugin_without_adapter.adapter is None

        with (
            patch("microsoft_teams.botbuilder.botbuilder_plugin.CloudAdapter") as mock_adapter_class,
            patch(
                "microsoft_teams.botbuilder.botbuilder_plugin.ConfigurationBotFrameworkAuthentication"
            ) as mock_config_class,
        ):
            mock_adapter_class.return_value = "mock_adapter"
            await plugin_without_adapter.on_init()

            mock_config_class.assert_called_once()
            mock_adapter_class.assert_called_once()
            assert plugin_without_adapter.adapter == "mock_adapter"

        # Should have registered route via http_server.adapter
        plugin_without_adapter.http_server.adapter.register_route.assert_called_once()
        call_args = plugin_without_adapter.http_server.adapter.register_route.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/api/messages"

    @pytest.mark.asyncio
    async def test_handle_activity_calls_adapter_and_handler(self, plugin_with_adapter: BotBuilderPlugin):
        """Test that _handle_activity calls adapter and handler."""
        activity_data = {
            "type": "message",
            "id": "activity-id",
            "from": {"id": "user1", "name": "Test User"},
            "recipient": {"id": "bot1", "name": "Test Bot"},
            "conversation": {"id": "conv1"},
            "serviceUrl": "https://service.url",
        }

        request = HttpRequest(
            body=activity_data,
            headers={"Authorization": "Bearer token"},
        )

        # Mock adapter.process_activity to call logic with a mock TurnContext
        async def fake_process_activity(auth_header, activity, logic):
            await logic(MagicMock(spec=TurnContext))

        assert plugin_with_adapter.adapter is not None
        plugin_with_adapter.adapter.process_activity = AsyncMock(side_effect=fake_process_activity)

        result = await plugin_with_adapter._handle_activity(request)

        # Ensure adapter.process_activity called with correct auth and activity
        plugin_with_adapter.adapter.process_activity.assert_called_once()
        called_auth, called_activity, _ = plugin_with_adapter.adapter.process_activity.call_args[0]
        assert called_auth == "Bearer token"
        assert isinstance(called_activity, Activity)

        # Ensure handler called via TurnContext
        plugin_with_adapter.handler.on_turn.assert_awaited()

        # Should have routed through HttpServer.handle_request
        plugin_with_adapter.http_server.handle_request.assert_awaited_once_with(request)

        # Should return a valid HttpResponse
        assert result["status"] == 200

    @pytest.mark.asyncio
    async def test_handle_activity_returns_error_on_adapter_error(self, plugin_with_adapter: BotBuilderPlugin):
        """Test that _handle_activity returns 500 on adapter error."""
        activity_data = {"type": "message", "id": "activity-id"}

        request = HttpRequest(
            body=activity_data,
            headers={},
        )

        assert plugin_with_adapter.adapter is not None
        plugin_with_adapter.adapter.process_activity = AsyncMock(side_effect=Exception("fail"))

        result = await plugin_with_adapter._handle_activity(request)

        assert result["status"] == 500
        assert result["body"]["detail"] == "fail"
