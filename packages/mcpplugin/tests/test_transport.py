"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.mcpplugin.transport import create_sse_transport, create_streamable_http_transport, create_transport

# pyright: basic


class TestCreateTransportFactory:
    """Tests for the create_transport factory function."""

    def test_unknown_transport_type_raises_value_error(self):
        """create_transport raises ValueError for unsupported transport types."""
        with pytest.raises(ValueError, match="Unsupported transport type: grpc"):
            create_transport("http://example.com", "grpc")

    def test_streamable_http_passes_url_and_headers(self):
        """create_transport forwards url and headers to create_streamable_http_transport."""
        headers = {"Authorization": "Bearer token"}
        with patch("microsoft_teams.mcpplugin.transport.create_streamable_http_transport") as mock_fn:
            create_transport("http://example.com", "streamable_http", headers)
            mock_fn.assert_called_once_with("http://example.com", headers)

    def test_sse_passes_url_and_headers(self):
        """create_transport forwards url and headers to create_sse_transport."""
        headers = {"X-Custom": "value"}
        with patch("microsoft_teams.mcpplugin.transport.create_sse_transport") as mock_fn:
            create_transport("http://example.com", "sse", headers)
            mock_fn.assert_called_once_with("http://example.com", headers)


class TestCreateStreamableHttpTransport:
    """Tests for create_streamable_http_transport."""

    async def test_no_headers_skips_httpx_async_client(self):
        """Without headers, httpx.AsyncClient is never instantiated."""
        read_stream = MagicMock()
        write_stream = MagicMock()

        @asynccontextmanager
        async def mock_streamable_http_client(url, http_client=None):
            yield (read_stream, write_stream, MagicMock())

        with (
            patch(
                "microsoft_teams.mcpplugin.transport.streamable_http_client",
                mock_streamable_http_client,
            ),
            patch("microsoft_teams.mcpplugin.transport.httpx.AsyncClient") as mock_async_client,
        ):
            async with create_streamable_http_transport("http://example.com"):
                pass

            mock_async_client.assert_not_called()

    async def test_static_string_headers_creates_http_client(self):
        """Static string headers are passed verbatim to httpx.AsyncClient."""
        read_stream = MagicMock()
        write_stream = MagicMock()

        mock_http_client_instance = MagicMock()

        @asynccontextmanager
        async def mock_streamable_http_client(url, http_client=None):
            yield (read_stream, write_stream, MagicMock())

        with (
            patch(
                "microsoft_teams.mcpplugin.transport.streamable_http_client",
                mock_streamable_http_client,
            ),
            patch("microsoft_teams.mcpplugin.transport.httpx.AsyncClient") as mock_async_client,
        ):
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_client_instance)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

            headers = {"Authorization": "Bearer token", "X-Version": "1.0"}
            async with create_streamable_http_transport("http://example.com", headers) as (r, w):
                assert r is read_stream
                assert w is write_stream

            mock_async_client.assert_called_once_with(headers={"Authorization": "Bearer token", "X-Version": "1.0"})

    async def test_sync_callable_header_is_resolved(self):
        """Sync callable header values are called and resolved to strings."""
        read_stream = MagicMock()
        write_stream = MagicMock()

        def get_token():
            return "Bearer sync-token"

        with (
            patch("microsoft_teams.mcpplugin.transport.streamable_http_client") as mock_streamable,
            patch("microsoft_teams.mcpplugin.transport.httpx.AsyncClient") as mock_async_client,
        ):
            mock_http_instance = MagicMock()
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

            @asynccontextmanager
            async def fake_streamable(url, http_client=None):
                yield (read_stream, write_stream, MagicMock())

            mock_streamable.side_effect = fake_streamable

            headers = {"Authorization": get_token}
            async with create_streamable_http_transport("http://example.com", headers):
                pass

            mock_async_client.assert_called_once_with(headers={"Authorization": "Bearer sync-token"})

    async def test_async_callable_header_is_awaited_and_resolved(self):
        """Async callable header values are awaited and resolved to strings."""
        read_stream = MagicMock()
        write_stream = MagicMock()

        async def get_async_token():
            return "Bearer async-token"

        with (
            patch("microsoft_teams.mcpplugin.transport.streamable_http_client") as mock_streamable,
            patch("microsoft_teams.mcpplugin.transport.httpx.AsyncClient") as mock_async_client,
        ):
            mock_http_instance = MagicMock()
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

            @asynccontextmanager
            async def fake_streamable(url, http_client=None):
                yield (read_stream, write_stream, MagicMock())

            mock_streamable.side_effect = fake_streamable

            headers = {"Authorization": get_async_token}
            async with create_streamable_http_transport("http://example.com", headers):
                pass

            mock_async_client.assert_called_once_with(headers={"Authorization": "Bearer async-token"})

    async def test_mixed_header_types_all_resolved(self):
        """Mix of static string, sync callable, and async callable headers are all resolved."""
        read_stream = MagicMock()
        write_stream = MagicMock()

        def sync_fn():
            return "sync-value"

        async def async_fn():
            return "async-value"

        with (
            patch("microsoft_teams.mcpplugin.transport.streamable_http_client") as mock_streamable,
            patch("microsoft_teams.mcpplugin.transport.httpx.AsyncClient") as mock_async_client,
        ):
            mock_http_instance = MagicMock()
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

            @asynccontextmanager
            async def fake_streamable(url, http_client=None):
                yield (read_stream, write_stream, MagicMock())

            mock_streamable.side_effect = fake_streamable

            headers = {
                "X-Static": "static-value",
                "X-Sync": sync_fn,
                "X-Async": async_fn,
            }
            async with create_streamable_http_transport("http://example.com", headers):
                pass

            mock_async_client.assert_called_once_with(
                headers={
                    "X-Static": "static-value",
                    "X-Sync": "sync-value",
                    "X-Async": "async-value",
                }
            )

    async def test_non_string_header_values_are_coerced_to_string(self):
        """Non-string header values (int, etc.) are coerced via str()."""
        read_stream = MagicMock()
        write_stream = MagicMock()

        with (
            patch("microsoft_teams.mcpplugin.transport.streamable_http_client") as mock_streamable,
            patch("microsoft_teams.mcpplugin.transport.httpx.AsyncClient") as mock_async_client,
        ):
            mock_http_instance = MagicMock()
            mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_http_instance)
            mock_async_client.return_value.__aexit__ = AsyncMock(return_value=False)

            @asynccontextmanager
            async def fake_streamable(url, http_client=None):
                yield (read_stream, write_stream, MagicMock())

            mock_streamable.side_effect = fake_streamable

            headers: Any = {"X-Port": 8080}
            async with create_streamable_http_transport("http://example.com", headers):
                pass

            mock_async_client.assert_called_once_with(headers={"X-Port": "8080"})

    async def test_yields_read_and_write_streams(self):
        """The context manager correctly yields (read_stream, write_stream) to callers."""
        read_stream = MagicMock(name="read")
        write_stream = MagicMock(name="write")

        with patch("microsoft_teams.mcpplugin.transport.streamable_http_client") as mock_streamable:

            @asynccontextmanager
            async def fake_streamable(url, http_client=None):
                yield (read_stream, write_stream, MagicMock())

            mock_streamable.side_effect = fake_streamable

            async with create_streamable_http_transport("http://example.com") as (r, w):
                assert r is read_stream
                assert w is write_stream


class TestCreateSseTransport:
    """Tests for create_sse_transport."""

    async def test_no_headers_calls_sse_client_with_empty_headers(self):
        """Without headers, sse_client is called with an empty resolved_headers dict."""
        read_stream = MagicMock()
        write_stream = MagicMock()
        captured: dict = {}

        @asynccontextmanager
        async def mock_sse_client(url, headers=None):
            captured["headers"] = headers
            yield (read_stream, write_stream)

        with patch(
            "microsoft_teams.mcpplugin.transport.sse_client",
            mock_sse_client,
        ):
            async with create_sse_transport("http://example.com") as (r, w):
                assert r is read_stream
                assert w is write_stream

        assert captured["headers"] == {}

    async def test_static_string_headers_passed_to_sse_client(self):
        """Static string headers are resolved and forwarded to sse_client."""
        read_stream = MagicMock()
        write_stream = MagicMock()
        captured: dict = {}

        @asynccontextmanager
        async def mock_sse_client(url, headers=None):
            captured["headers"] = headers
            yield (read_stream, write_stream)

        with patch(
            "microsoft_teams.mcpplugin.transport.sse_client",
            mock_sse_client,
        ):
            headers = {"Authorization": "Bearer static", "Content-Type": "application/json"}
            async with create_sse_transport("http://example.com", headers) as (r, w):
                assert r is read_stream
                assert w is write_stream

        assert captured["headers"] == {"Authorization": "Bearer static", "Content-Type": "application/json"}

    async def test_sync_callable_header_resolved_for_sse(self):
        """Sync callable header values are called and resolved before passing to sse_client."""
        captured: dict = {}

        def get_token():
            return "Bearer sync-sse-token"

        @asynccontextmanager
        async def mock_sse_client(url, headers=None):
            captured["headers"] = headers
            yield (MagicMock(), MagicMock())

        with patch(
            "microsoft_teams.mcpplugin.transport.sse_client",
            mock_sse_client,
        ):
            headers = {"Authorization": get_token}
            async with create_sse_transport("http://example.com", headers):
                pass

        assert captured["headers"] == {"Authorization": "Bearer sync-sse-token"}

    async def test_async_callable_header_resolved_for_sse(self):
        """Async callable header values are awaited and resolved before passing to sse_client."""
        captured: dict = {}

        async def get_async_token():
            return "Bearer async-sse-token"

        @asynccontextmanager
        async def mock_sse_client(url, headers=None):
            captured["headers"] = headers
            yield (MagicMock(), MagicMock())

        with patch(
            "microsoft_teams.mcpplugin.transport.sse_client",
            mock_sse_client,
        ):
            headers = {"Authorization": get_async_token}
            async with create_sse_transport("http://example.com", headers):
                pass

        assert captured["headers"] == {"Authorization": "Bearer async-sse-token"}

    async def test_mixed_header_types_resolved_for_sse(self):
        """Mix of static, sync callable, and async callable headers are all resolved for SSE."""
        captured: dict = {}

        def sync_fn():
            return "sync-val"

        async def async_fn():
            return "async-val"

        @asynccontextmanager
        async def mock_sse_client(url, headers=None):
            captured["headers"] = headers
            yield (MagicMock(), MagicMock())

        with patch(
            "microsoft_teams.mcpplugin.transport.sse_client",
            mock_sse_client,
        ):
            headers = {
                "X-Static": "static-val",
                "X-Sync": sync_fn,
                "X-Async": async_fn,
            }
            async with create_sse_transport("http://example.com", headers):
                pass

        assert captured["headers"] == {
            "X-Static": "static-val",
            "X-Sync": "sync-val",
            "X-Async": "async-val",
        }

    async def test_sse_non_string_header_values_coerced(self):
        """Non-string SSE header values (int, bool, etc.) are coerced via str()."""
        captured: dict = {}

        @asynccontextmanager
        async def mock_sse_client(url, headers=None):
            captured["headers"] = headers
            yield (MagicMock(), MagicMock())

        with patch(
            "microsoft_teams.mcpplugin.transport.sse_client",
            mock_sse_client,
        ):
            headers: Any = {"X-Retry": 3}
            async with create_sse_transport("http://example.com", headers):
                pass

        assert captured["headers"] == {"X-Retry": "3"}
