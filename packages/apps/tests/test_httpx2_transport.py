"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx2
import pytest
from microsoft_teams.apps import App
from microsoft_teams.apps.diagnostics._helpers import trace_oauth_operation
from microsoft_teams.apps.files.download import FileFetchTarget, GraphCredential, open_file_stream
from microsoft_teams.apps.socket_mode.negotiate import negotiate_service, negotiate_signalr
from microsoft_teams.common import Client, ClientOptions
from opentelemetry.trace import StatusCode


async def test_app_nonsharing_clones_and_api_scopes_use_httpx2():
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(200))) as raw:
        supplied = Client(ClientOptions(headers={"User-Agent": "customer/1"}), _http=raw)
        app = App(client=supplied)
        try:
            assert isinstance(app.http_client.http, httpx2.AsyncClient)
            assert app.http_client.http is not raw
            assert app.api.http.http is not app.http_client.http
            assert app.http_client.http.timeout == httpx2.Timeout(None)
            assert app.api.from_service_url("https://example.test").http.http is app.api.http.http
            assert "customer/1" in app.http_client.http.headers["user-agent"]
            assert "teams.py[apps]/" in app.http_client.http.headers["user-agent"]
        finally:
            await app.http_client.http.aclose()
            await app.api.http.http.aclose()
        assert not raw.is_closed


async def test_oauth_diagnostics_classifies_real_httpx2_status_error():
    tracer = MagicMock()
    span = tracer.start_as_current_span.return_value.__enter__.return_value
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(403))) as raw:
        with (
            patch("microsoft_teams.apps.diagnostics._helpers.get_tracer", return_value=tracer),
            patch("microsoft_teams.apps.diagnostics._helpers.record_oauth_error") as errors,
            patch("microsoft_teams.apps.diagnostics._helpers.record_oauth_operation") as operations,
            pytest.raises(httpx2.HTTPStatusError) as raised,
            trace_oauth_operation("graph", "signin"),
        ):
            await Client(_http=raw).get("https://example.test/token")
    errors.assert_called_once_with("graph", "signin", "http_error")
    operations.assert_called_once()
    span.record_exception.assert_called_once_with(raised.value)
    assert span.set_status.call_args.args[0].status_code == StatusCode.ERROR


class PausingStream(httpx2.AsyncByteStream):
    def __init__(self):
        self.closed = False

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"first"
        await asyncio.Event().wait()

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.parametrize("graph", [False, True])
@pytest.mark.parametrize("cancelled", [False, True])
@pytest.mark.parametrize("borrowed", [False, True])
async def test_file_stream_cleanup_preserves_client_ownership(
    graph: bool, cancelled: bool, borrowed: bool, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    stream = PausingStream()
    response = httpx2.Response(200, stream=stream)

    async def token() -> str:
        return "graph-token"

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: response), trust_env=False) as raw:
        if borrowed:
            monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "missing.pem"))
        else:
            monkeypatch.setattr("microsoft_teams.apps.files.download.httpx2.AsyncClient", lambda: raw)
        target = FileFetchTarget(
            scope="personal",
            content_url="https://example.test/shared" if graph else None,
            download_url=None if graph else "https://example.test/download",
        )
        started = asyncio.Event()

        async def consume() -> None:
            async with open_file_stream(
                target, client=raw if borrowed else None, credential=GraphCredential("app", token)
            ) as opened:
                assert await opened.chunks.__anext__() == b"first"
                started.set()
                if cancelled:
                    await opened.chunks.__anext__()

        task = asyncio.create_task(consume())
        await asyncio.wait_for(started.wait(), 2)
        if cancelled:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            await task
        assert stream.closed
        assert response.is_closed
        assert raw.timeout == httpx2.Timeout(5)
        assert raw.is_closed is not borrowed


@pytest.mark.parametrize("signalr", [False, True])
@pytest.mark.parametrize("borrowed", [False, True])
async def test_negotiate_timeout_preserves_default_transport_timeout_and_client_ownership(
    signalr: bool, borrowed: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    requests: list[httpx2.Request] = []

    async def wait(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        await asyncio.Event().wait()
        raise AssertionError("unreachable")

    raw = httpx2.AsyncClient(transport=httpx2.MockTransport(wait), trust_env=False)
    if borrowed:
        monkeypatch.setenv("SSL_CERT_FILE", str(tmp_path / "missing.pem"))
    else:
        monkeypatch.setattr("microsoft_teams.apps.socket_mode.negotiate.httpx2.AsyncClient", lambda: raw)
    try:
        with pytest.raises(TimeoutError):
            if signalr:
                await negotiate_signalr(
                    "https://example.test/hub", "token", http_client=raw if borrowed else None, timeout=0.01
                )
            else:
                await negotiate_service(
                    "https://example.test/connect", _bot_token, http_client=raw if borrowed else None, timeout=0.01
                )
        assert len(requests) == 1
        assert requests[0].extensions["timeout"] == dict(connect=5, read=5, write=5, pool=5)
        assert raw.is_closed is not borrowed
    finally:
        await raw.aclose()


async def _bot_token() -> str:
    return "bot-token"
