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
from fastapi import HTTPException, Request, Response
from microsoft_teams.api import Credentials
from microsoft_teams.botbuilder import BotBuilderPlugin


class TestBotBuilderPlugin:
    """Tests for BotBuilderPlugin."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock()

    @pytest.fixture
    def plugin_without_adapter(self):
        plugin = BotBuilderPlugin(skip_auth=True)
        plugin.credentials = MagicMock(spec=Credentials)
        plugin.credentials.client_id = "abc"
        plugin.credentials.client_secret = "secret"
        plugin.credentials.tenant_id = "tenant-123"
        return plugin

    @pytest.fixture
    def plugin_with_adapter(self) -> BotBuilderPlugin:
        adapter = MagicMock(spec=CloudAdapter)
        plugin = BotBuilderPlugin(adapter=adapter, skip_auth=True)
        plugin._handle_activity_request = AsyncMock(return_value="fake_result")  # pyright: ignore[reportPrivateUsage]
        handler = AsyncMock(spec=ActivityHandler)
        plugin.handler = handler
        return plugin

    @pytest.mark.asyncio
    async def test_on_init_creates_adapter_when_missing(self, plugin_without_adapter: BotBuilderPlugin):
        assert plugin_without_adapter.adapter is None

        with (
            patch("microsoft.teams.botbuilder.botbuilder_plugin.CloudAdapter") as mock_adapter_class,
            patch(
                "microsoft.teams.botbuilder.botbuilder_plugin.ConfigurationBotFrameworkAuthentication"
            ) as mock_config_class,
        ):
            mock_adapter_class.return_value = "mock_adapter"
            await plugin_without_adapter.on_init()

            mock_config_class.assert_called_once()
            mock_adapter_class.assert_called_once()
            assert plugin_without_adapter.adapter == "mock_adapter"

    @pytest.mark.asyncio
    async def test_on_activity_request_calls_adapter_and_handler(self, plugin_with_adapter: BotBuilderPlugin):
        # Mock request and response
        activity_data = {
            "type": "message",
            "id": "activity-id",
            "from": {"id": "user1", "name": "Test User"},
            "recipient": {"id": "bot1", "name": "Test Bot"},
            "conversation": {"id": "conv1"},
            "serviceUrl": "https://service.url",
        }
        request = AsyncMock(spec=Request)
        request.json.return_value = activity_data
        request.headers = {"Authorization": "Bearer token"}

        response = MagicMock(spec=Response)

        # Mock adapter.process_activity to call logic with a mock TurnContext
        async def fake_process_activity(auth_header, activity, logic):  # type: ignore
            print("Inside fake_process_activity")
            await logic(MagicMock(spec=TurnContext))

        assert plugin_with_adapter.adapter is not None

        plugin_with_adapter.adapter.process_activity = AsyncMock(side_effect=fake_process_activity)

        await plugin_with_adapter.on_activity_request(request, response)

        # Ensure adapter.process_activity called with correct auth and activity
        plugin_with_adapter.adapter.process_activity.assert_called_once()
        called_auth, called_activity, _ = plugin_with_adapter.adapter.process_activity.call_args[0]
        assert called_auth == "Bearer token"
        assert isinstance(called_activity, Activity)

        # Ensure handler called via TurnContext
        plugin_with_adapter.handler.on_turn.assert_awaited()  # type: ignore

    @pytest.mark.asyncio
    async def test_on_activity_request_raises_http_exception_on_adapter_error(
        self, plugin_with_adapter: BotBuilderPlugin
    ):
        activity_data = {"type": "message", "id": "activity-id"}
        request = AsyncMock(spec=Request)
        request.json.return_value = activity_data
        request.headers = {}

        response = MagicMock(spec=Response)
        assert plugin_with_adapter.adapter is not None

        plugin_with_adapter.adapter.process_activity = AsyncMock(side_effect=Exception("fail"))

        with pytest.raises(HTTPException) as exc:
            await plugin_with_adapter.on_activity_request(request, response)
        assert exc.value.status_code == 500
