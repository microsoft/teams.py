# pyright: reportMissingTypeStubs=false
"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botbuilder.core import ActivityHandler, TurnContext
from botbuilder.integration.aiohttp import CloudAdapter
from botbuilder.schema import Activity
from microsoft_teams.apps.http import HttpRequest, HttpResponse, HttpRouteHandler
from microsoft_teams.botbuilder import BotBuilderAdapter


class MockHttpServerAdapter:
    def __init__(self):
        self.routes = []
        self.static_routes = []
        self.started_with = None
        self.stopped = False

    def register_route(self, method, path, handler):
        self.routes.append((method, path, handler))

    def serve_static(self, path, directory):
        self.static_routes.append((path, directory))

    async def start(self, port):
        self.started_with = port

    async def stop(self):
        self.stopped = True


class TestBotBuilderAdapter:
    @pytest.fixture
    def underlying_adapter(self):
        return MockHttpServerAdapter()

    @pytest.fixture
    def cloud_adapter(self):
        adapter = MagicMock(spec=CloudAdapter)
        adapter.process_activity = AsyncMock()
        return adapter

    @pytest.fixture
    def botbuilder_adapter(self, underlying_adapter, cloud_adapter):
        handler = AsyncMock(spec=ActivityHandler)
        return BotBuilderAdapter(
            cloud_adapter=cloud_adapter,
            http_server_adapter=underlying_adapter,
            handler=handler,
        )

    def test_register_route_wraps_post_handler(self, botbuilder_adapter, underlying_adapter):
        async def teams_handler(request: HttpRequest) -> HttpResponse:
            return HttpResponse(status=200, body=None)

        botbuilder_adapter.register_route("POST", "/api/messages", teams_handler)

        assert len(underlying_adapter.routes) == 1
        method, path, handler = underlying_adapter.routes[0]
        assert method == "POST"
        assert path == "/api/messages"
        assert handler is not teams_handler

    @pytest.mark.asyncio
    async def test_handle_activity_calls_botbuilder_then_teams(
        self, botbuilder_adapter, underlying_adapter, cloud_adapter
    ):
        async def fake_process_activity(auth_header, activity, logic):
            await logic(MagicMock(spec=TurnContext, activity=SimpleNamespace(id="activity-id")))

        cloud_adapter.process_activity.side_effect = fake_process_activity
        teams_handler = AsyncMock(return_value=HttpResponse(status=200, body="teams"))
        botbuilder_adapter.register_route("POST", "/api/messages", teams_handler)
        route_handler: HttpRouteHandler = underlying_adapter.routes[0][2]

        request = HttpRequest(
            body={
                "type": "message",
                "id": "activity-id",
                "from": {"id": "user1", "name": "Test User"},
                "recipient": {"id": "bot1", "name": "Test Bot"},
                "conversation": {"id": "conv1"},
                "serviceUrl": "https://service.url",
            },
            headers={"Authorization": "Bearer token"},
        )

        result = await route_handler(request)

        cloud_adapter.process_activity.assert_awaited_once()
        called_auth, called_activity, _ = cloud_adapter.process_activity.call_args[0]
        assert called_auth == "Bearer token"
        assert isinstance(called_activity, Activity)
        botbuilder_adapter.handler.on_turn.assert_awaited_once()
        teams_handler.assert_awaited_once_with(request)
        assert result == HttpResponse(status=200, body="teams")

    @pytest.mark.asyncio
    async def test_sends_botbuilder_invoke_response_when_handled(
        self, botbuilder_adapter, underlying_adapter, cloud_adapter
    ):
        cloud_adapter.process_activity.return_value = SimpleNamespace(status=200, body={"source": "botbuilder"})
        teams_handler = AsyncMock(return_value=HttpResponse(status=200, body={"source": "teams"}))
        botbuilder_adapter.register_route("POST", "/api/messages", teams_handler)
        route_handler: HttpRouteHandler = underlying_adapter.routes[0][2]

        result = await route_handler(
            HttpRequest(body={"type": "invoke", "id": "activity-id", "name": "adaptiveCard/action"}, headers={})
        )

        assert result == HttpResponse(status=200, body={"source": "botbuilder"})
        teams_handler.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_falls_through_when_botbuilder_invoke_not_implemented(
        self, botbuilder_adapter, underlying_adapter, cloud_adapter
    ):
        cloud_adapter.process_activity.return_value = SimpleNamespace(status=501, body=None)
        teams_handler = AsyncMock(return_value=HttpResponse(status=200, body={"source": "teams"}))
        botbuilder_adapter.register_route("POST", "/api/messages", teams_handler)
        route_handler: HttpRouteHandler = underlying_adapter.routes[0][2]

        result = await route_handler(
            HttpRequest(body={"type": "invoke", "id": "activity-id", "name": "adaptiveCard/action"}, headers={})
        )

        assert result == HttpResponse(status=200, body={"source": "teams"})
        teams_handler.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_body_falls_through_without_botbuilder(
        self, botbuilder_adapter, underlying_adapter, cloud_adapter
    ):
        teams_handler = AsyncMock(return_value=HttpResponse(status=200, body="teams"))
        botbuilder_adapter.register_route("POST", "/api/messages", teams_handler)
        route_handler: HttpRouteHandler = underlying_adapter.routes[0][2]

        result = await route_handler(HttpRequest(body={}, headers={}))

        cloud_adapter.process_activity.assert_not_awaited()
        teams_handler.assert_awaited_once()
        assert result == HttpResponse(status=200, body="teams")

    @pytest.mark.asyncio
    async def test_returns_generic_error_when_botbuilder_processing_fails(
        self, botbuilder_adapter, underlying_adapter, cloud_adapter, caplog
    ):
        cloud_adapter.process_activity.side_effect = Exception("secret failure detail")
        teams_handler = AsyncMock(return_value=HttpResponse(status=200, body="teams"))
        botbuilder_adapter.register_route("POST", "/api/messages", teams_handler)
        route_handler: HttpRouteHandler = underlying_adapter.routes[0][2]

        result = await route_handler(HttpRequest(body={"type": "message", "id": "activity-id"}, headers={}))

        assert result == HttpResponse(status=500, body={"error": "Internal server error"})
        assert any("Error processing activity" in record.message for record in caplog.records)

    def test_constructs_cloud_adapter_from_microsoft_app_environment(self, monkeypatch):
        monkeypatch.setenv("MicrosoftAppId", "app-id")
        monkeypatch.setenv("MicrosoftAppPassword", "secret")
        monkeypatch.setenv("MicrosoftAppTenantId", "tenant-id")
        monkeypatch.setenv("MicrosoftAppType", "singletenant")

        with patch("microsoft_teams.botbuilder.adapter.CloudAdapter") as mock_adapter_class:
            mock_adapter_class.return_value = "mock_adapter"
            adapter = BotBuilderAdapter()

        assert adapter.cloud_adapter == "mock_adapter"

    def test_constructs_cloud_adapter_from_teams_app_environment(self, monkeypatch):
        monkeypatch.setenv("CLIENT_ID", "app-id")
        monkeypatch.setenv("CLIENT_SECRET", "secret")
        monkeypatch.setenv("TENANT_ID", "tenant-id")

        with patch("microsoft_teams.botbuilder.adapter.CloudAdapter") as mock_adapter_class:
            mock_adapter_class.return_value = "mock_adapter"
            adapter = BotBuilderAdapter()

        assert adapter.cloud_adapter == "mock_adapter"

    def test_throws_when_no_cloud_adapter_or_credentials_available(self, monkeypatch):
        monkeypatch.delenv("MicrosoftAppId", raising=False)
        monkeypatch.delenv("MicrosoftAppPassword", raising=False)
        monkeypatch.delenv("MicrosoftAppTenantId", raising=False)
        monkeypatch.delenv("MicrosoftAppType", raising=False)
        monkeypatch.delenv("CLIENT_ID", raising=False)
        monkeypatch.delenv("CLIENT_SECRET", raising=False)
        monkeypatch.delenv("TENANT_ID", raising=False)

        with pytest.raises(ValueError, match="BotBuilderAdapter requires credentials"):
            BotBuilderAdapter()
