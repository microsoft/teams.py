"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import (
    ConfigResponse,
    InvokeResponse,
)
from microsoft_teams.apps.http import FastAPIAdapter
from microsoft_teams.apps.http.adapter import HttpRequest, HttpResponse
from microsoft_teams.apps.http.http_server import HttpServer


class TestHttpServer:
    """Test cases for HttpServer implementation."""

    def test_http_server_is_publicly_exported(self):
        """HttpServer remains publicly exported for compatibility."""
        import microsoft_teams.apps as apps
        import microsoft_teams.apps.http as http

        assert "HttpServer" in apps.__all__
        assert apps.HttpServer is HttpServer
        assert "HttpServer" in http.__all__
        assert http.HttpServer is HttpServer

    @pytest.fixture
    def mock_adapter(self):
        """Create a mock adapter."""
        adapter = MagicMock()
        adapter.register_route = MagicMock()
        adapter.serve_static = MagicMock()
        adapter.start = AsyncMock()
        adapter.stop = AsyncMock()
        return adapter

    @pytest.fixture
    def server(self, mock_adapter):
        """Create HttpServer with mock adapter."""
        return HttpServer(mock_adapter)

    def test_init(self, server, mock_adapter):
        """Test HttpServer initialization."""
        assert server.adapter is mock_adapter
        assert server.on_request is None

    def test_initialize_idempotent(self, server, mock_adapter):
        """Test that initialize can be called multiple times safely."""
        server.initialize(dangerously_allow_unauthenticated_requests=True)
        server.initialize(dangerously_allow_unauthenticated_requests=True)
        # Should only register route once
        assert mock_adapter.register_route.call_count == 1

    def test_initialize_accepts_skip_auth_alias(self, server, mock_adapter):
        """skip_auth remains a deprecated alias for unauthenticated local development."""
        server.initialize(skip_auth=True)

        assert server._dangerously_allow_unauthenticated_requests is True
        mock_adapter.register_route.assert_called_once()

    def test_invalid_messaging_endpoint_raises(self, mock_adapter):
        """Test that invalid messaging endpoint raises ValueError."""
        with pytest.raises(ValueError, match="must be a non-empty path"):
            HttpServer(mock_adapter, messaging_endpoint="no-slash")

    def test_messaging_endpoint_default(self, server):
        """Test default messaging endpoint."""
        assert server.messaging_endpoint == "/api/messages"

    def test_initialize_registers_route(self, server, mock_adapter):
        """Test that initialize registers the /api/messages route."""
        server.initialize()
        mock_adapter.register_route.assert_called_once()
        call_args = mock_adapter.register_route.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/api/messages"

    def test_initialize_registers_custom_messaging_endpoint(self, mock_adapter):
        """Test that initialize registers a custom messaging endpoint."""
        custom_server = HttpServer(mock_adapter, messaging_endpoint="/bot/incoming")
        assert custom_server.messaging_endpoint == "/bot/incoming"

        custom_server.initialize()
        mock_adapter.register_route.assert_called_once()
        call_args = mock_adapter.register_route.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/bot/incoming"

    def test_initialize_warns_when_no_credentials(self, server, caplog):
        """Bot started without credentials should log a warning about anonymous traffic."""
        import logging

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.http.http_server"):
            server.initialize(credentials=None)

        assert any("No credentials configured" in record.message for record in caplog.records)

    def test_initialize_does_not_warn_with_credentials(self, server, caplog):
        """Bot started with credentials should not log the anonymous warning."""
        import logging

        creds = MagicMock()
        creds.client_id = "test-app"
        creds.tenant_id = "test-tenant"

        with caplog.at_level(logging.WARNING, logger="microsoft_teams.apps.http.http_server"):
            server.initialize(credentials=creds)

        assert not any("No credentials configured" in record.message for record in caplog.records)

    def test_on_request_setter(self, server):
        """Test on_request callback setter."""

        async def handler(event):
            return InvokeResponse(status=200)

        server.on_request = handler
        assert server.on_request is handler

    @pytest.mark.asyncio
    async def test_handle_activity_success(self, server):
        """Test successful activity handling."""
        expected_body = {"status": "success"}
        expected_response = InvokeResponse(body=cast(ConfigResponse, expected_body), status=200)

        async def mock_handler(event):
            return expected_response

        server.on_request = mock_handler
        server.initialize(dangerously_allow_unauthenticated_requests=True)

        request = HttpRequest(
            body={
                "type": "message",
                "id": "test-123",
                "text": "Test message",
            },
            headers={},
        )

        result = await server.handle_request(request)

        assert result["status"] == 200
        assert result["body"] == expected_body

    @pytest.mark.asyncio
    async def test_handle_activity_exception(self, server):
        """Test activity handling when handler raises exception."""

        async def failing_handler(event):
            raise ValueError("Handler failed")

        server.on_request = failing_handler
        server.initialize(dangerously_allow_unauthenticated_requests=True)

        request = HttpRequest(
            body={"type": "message", "id": "test-123"},
            headers={},
        )

        result = await server.handle_request(request)

        assert result["status"] == 500

    @pytest.mark.asyncio
    async def test_handle_activity_no_handler(self, server):
        """Test activity handling when no on_request handler is set."""
        server.initialize(dangerously_allow_unauthenticated_requests=True)

        request = HttpRequest(
            body={"type": "message", "id": "test-123"},
            headers={},
        )

        result = await server.handle_request(request)

        assert result["status"] == 500

    @pytest.mark.asyncio
    async def test_rejects_missing_bearer_token(self, server, mock_adapter):
        """Test that auth-enabled server rejects requests without Bearer token."""
        from unittest.mock import MagicMock

        creds = MagicMock()
        creds.client_id = "test-app-id"
        server.initialize(credentials=creds)

        request = HttpRequest(
            body={"type": "message", "id": "test-123"},
            headers={"authorization": "Basic invalid"},
        )

        result = await server.handle_request(request)
        assert result["status"] == 401

    @pytest.mark.asyncio
    async def test_rejects_invalid_jwt(self, server, mock_adapter):
        """Test that auth-enabled server rejects invalid JWT tokens."""
        from unittest.mock import MagicMock

        creds = MagicMock()
        creds.client_id = "test-app-id"
        server.initialize(credentials=creds)

        request = HttpRequest(
            body={"type": "message", "id": "test-123"},
            headers={"authorization": "Bearer invalid.jwt.token"},
        )

        result = await server.handle_request(request)
        assert result["status"] == 401


class TestHttpServerNoCredentials:
    """Test cases for HttpServer when no credentials are configured and unauthenticated requests are not allowed."""

    @pytest.fixture
    def mock_adapter(self):
        adapter = MagicMock()
        adapter.register_route = MagicMock()
        adapter.start = AsyncMock()
        adapter.stop = AsyncMock()
        return adapter

    @pytest.fixture
    def server(self, mock_adapter):
        server = HttpServer(mock_adapter)
        server.initialize(credentials=None, dangerously_allow_unauthenticated_requests=False)
        return server

    @pytest.mark.asyncio
    async def test_rejects_request_when_no_credentials(self, server):
        """Test that requests are rejected with 401 when no credentials are configured."""
        server.on_request = AsyncMock(return_value=InvokeResponse(status=200))

        request = HttpRequest(
            body={
                "type": "message",
                "id": "test-123",
                "serviceUrl": "https://attacker.com",
            },
            headers={},
        )

        result = await server.handle_request(request)

        assert result["status"] == 401
        assert result["body"] == {"error": "Authentication not configured"}
        server.on_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_rejects_request_with_auth_header_when_no_credentials(self, server):
        """Test that even requests with auth headers are rejected when no credentials are configured."""
        server.on_request = AsyncMock(return_value=InvokeResponse(status=200))

        request = HttpRequest(
            body={
                "type": "message",
                "id": "test-123",
                "serviceUrl": "https://example.com",
            },
            headers={"authorization": "Bearer some-token"},
        )

        result = await server.handle_request(request)

        assert result["status"] == 401
        assert result["body"] == {"error": "Authentication not configured"}
        server.on_request.assert_not_called()


class TestFastAPIAdapter:
    """Test cases for FastAPIAdapter."""

    def test_init_creates_fastapi_app(self):
        """Test FastAPIAdapter creates a FastAPI app."""
        from fastapi import FastAPI

        adapter = FastAPIAdapter()
        assert isinstance(adapter.app, FastAPI)

    def test_register_route(self):
        """Test route registration on FastAPI app."""
        adapter = FastAPIAdapter()

        async def handler(request: HttpRequest) -> HttpResponse:
            return HttpResponse(status=200, body=None)

        adapter.register_route("POST", "/test", handler)

        # Verify a route was registered on the FastAPI app
        routes = [r for r in adapter.app.routes if getattr(r, "path", None) == "/test"]
        assert len(routes) == 1

    def test_serve_static(self, tmp_path):
        """Test static file mounting."""
        adapter = FastAPIAdapter()
        adapter.serve_static("/static", str(tmp_path))

        # Verify a mount was registered
        mounts = [r for r in adapter.app.routes if getattr(r, "path", None) == "/static"]
        assert len(mounts) == 1

    @pytest.mark.asyncio
    async def test_start_creates_uvicorn_server(self):
        """Test that start creates and starts a uvicorn server."""
        adapter = FastAPIAdapter()

        mock_server = MagicMock()
        mock_server.serve = AsyncMock()

        with (
            patch("microsoft_teams.apps.http.fastapi_adapter.uvicorn.Config") as mock_config,
            patch("microsoft_teams.apps.http.fastapi_adapter.uvicorn.Server", return_value=mock_server),
        ):
            mock_config.return_value = MagicMock()
            await adapter.start(3978)

            mock_config.assert_called_once()
            mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stop signals the server."""
        adapter = FastAPIAdapter()
        mock_server = MagicMock()
        adapter._server = mock_server

        await adapter.stop()

        assert mock_server.should_exit is True

    @pytest.mark.asyncio
    async def test_stop_no_server(self):
        """Test stop when no server is running."""
        adapter = FastAPIAdapter()
        # Should not raise
        await adapter.stop()

    def test_server_factory(self):
        """Test custom server factory."""
        mock_server = MagicMock()

        def factory(app):
            mock_server.config = MagicMock()
            mock_server.config.app = app
            return mock_server

        adapter = FastAPIAdapter(server_factory=factory)
        assert adapter._server is mock_server

    def test_server_factory_wrong_app_raises(self):
        """Test that server factory with wrong app raises."""
        mock_server = MagicMock()
        mock_server.config.app = MagicMock()  # Different app instance

        def factory(app):
            return mock_server

        with pytest.raises(ValueError, match="server_factory must return"):
            FastAPIAdapter(server_factory=factory)
