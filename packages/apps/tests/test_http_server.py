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
from microsoft_teams.apps.http import FastAPIAdapter, HttpServer
from microsoft_teams.apps.http.adapter import HttpRequest, HttpResponse


class TestHttpServer:
    """Test cases for HttpServer public interface."""

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

    def test_initialize_registers_route(self, server, mock_adapter):
        """Test that initialize registers the /api/messages route."""
        server.initialize()
        mock_adapter.register_route.assert_called_once()
        call_args = mock_adapter.register_route.call_args
        assert call_args[0][0] == "POST"
        assert call_args[0][1] == "/api/messages"

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
        server.initialize(skip_auth=True)

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
        server.initialize(skip_auth=True)

        request = HttpRequest(
            body={"type": "message", "id": "test-123"},
            headers={},
        )

        result = await server.handle_request(request)

        assert result["status"] == 500

    @pytest.mark.asyncio
    async def test_handle_activity_no_handler(self, server):
        """Test activity handling when no on_request handler is set."""
        server.initialize(skip_auth=True)

        request = HttpRequest(
            body={"type": "message", "id": "test-123"},
            headers={},
        )

        result = await server.handle_request(request)

        assert result["status"] == 500


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

        async def handler(req: HttpRequest) -> HttpResponse:
            return HttpResponse(status=200, body=None)

        adapter.register_route("POST", "/test", handler)

        # Verify a route was registered on the FastAPI app
        routes = [r for r in adapter.app.routes if hasattr(r, "path") and r.path == "/test"]
        assert len(routes) == 1

    def test_serve_static(self, tmp_path):
        """Test static file mounting."""
        adapter = FastAPIAdapter()
        adapter.serve_static("/static", str(tmp_path))

        # Verify a mount was registered
        mounts = [r for r in adapter.app.routes if hasattr(r, "path") and r.path == "/static"]
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
