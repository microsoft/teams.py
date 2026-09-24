"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import json
from typing import Awaitable, Callable, Optional, Union

import httpx
import pytest
from microsoft_teams.apps.socket_mode import connection as connection_module
from microsoft_teams.apps.socket_mode.connection import (
    SignalRSocketConnection,
    SocketConnectionAborted,
    SocketConnectionContext,
)
from microsoft_teams.apps.socket_mode.signalr import RECORD_SEPARATOR, SignalRProtocolError
from microsoft_teams.apps.socket_mode.types import (
    ReplyFrame,
    SocketActivityEnvelope,
    SocketConnectionHandlers,
    SocketReadyFrame,
)


class MockWebSocket:
    def __init__(self):
        self.incoming: asyncio.Queue[Union[str, bytes, Exception]] = asyncio.Queue()
        self.sent: list[str] = []
        self.closed = 0

    async def send(self, message: str) -> None:
        self.sent.append(message)

    async def recv(self) -> Union[str, bytes]:
        item = await self.incoming.get()
        if isinstance(item, Exception):
            raise item
        return item

    async def close(self) -> None:
        self.closed += 1
        self.incoming.put_nowait(ConnectionError("closed"))


def make_http_client(*, hub_url: str = "https://signalr.example/client/?hub=teams") -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "botapi.example":
            return httpx.Response(
                200,
                json={"url": hub_url, "accessToken": "signalr-token", "expiresIn": 120},
            )
        return httpx.Response(
            200,
            json={
                "connectionToken": "connection-token",
                "availableTransports": [{"transport": "WebSockets", "transferFormats": ["Text"]}],
            },
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def make_handlers(
    *,
    on_activity: Optional[Callable[[SocketActivityEnvelope], Awaitable[Optional[ReplyFrame]]]] = None,
    on_ready: Optional[Callable[[SocketReadyFrame], None]] = None,
    on_closed: Optional[Callable[[Optional[Exception]], None]] = None,
) -> SocketConnectionHandlers:
    async def default_activity(_: SocketActivityEnvelope) -> Optional[ReplyFrame]:
        return None

    return SocketConnectionHandlers(
        on_activity=on_activity or default_activity,
        on_ready=on_ready or (lambda _: None),
        on_closed=on_closed or (lambda _: None),
    )


def make_context(**overrides: float) -> SocketConnectionContext:
    values = {
        "readiness_timeout": 1.0,
        "keep_alive_interval": 30.0,
        "server_timeout": 30.0,
        "websocket_open_timeout": 1.0,
    }
    values.update(overrides)
    return SocketConnectionContext(
        negotiate_url="https://botapi.example/v3/websockets/connect",
        get_bot_token=lambda: _token("bot-token"),
        **values,
    )


@pytest.mark.asyncio
async def test_connection_waits_for_socket_ready_and_returns_client_result():
    websocket = MockWebSocket()
    ready_frames: list[SocketReadyFrame] = []
    activity_seen = asyncio.Event()

    async def on_activity(envelope: SocketActivityEnvelope) -> ReplyFrame:
        activity_seen.set()
        return ReplyFrame(status=201, envelope_id=envelope.envelope_id, body={"ok": True})

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(on_activity=on_activity, on_ready=ready_frames.append),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        start = asyncio.create_task(connection.start())
        await _eventually(lambda: len(websocket.sent) == 1)
        websocket.incoming.put_nowait(f"{{}}{RECORD_SEPARATOR}")
        await asyncio.sleep(0)
        assert not start.done()

        websocket.incoming.put_nowait(
            json.dumps(
                {
                    "type": 1,
                    "target": "SocketReady",
                    "arguments": [{"botKey": "bot-1", "connectionId": "conn-1"}],
                }
            )
            + RECORD_SEPARATOR
        )
        await start
        assert ready_frames == [SocketReadyFrame(bot_key="bot-1", connection_id="conn-1")]
        assert connection.expires_in_seconds == 120

        websocket.incoming.put_nowait(
            json.dumps(
                {
                    "type": 1,
                    "invocationId": "inv-1",
                    "target": "Activity",
                    "arguments": [{"envelopeId": "env-1", "payload": {"type": "invoke"}}],
                }
            )
            + RECORD_SEPARATOR
        )
        await activity_seen.wait()
        await _eventually(lambda: len(websocket.sent) == 2)
        completion = json.loads(websocket.sent[1].removesuffix(RECORD_SEPARATOR))
        assert completion["type"] == 3
        assert completion["invocationId"] == "inv-1"
        assert completion["result"]["status"] == 201
        await connection.stop()


@pytest.mark.asyncio
async def test_connection_closes_when_readiness_times_out():
    websocket = MockWebSocket()
    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(readiness_timeout=0.01),
            make_handlers(),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        websocket.incoming.put_nowait(f"{{}}{RECORD_SEPARATOR}")

        with pytest.raises(TimeoutError, match="Socket Mode connection timed out"):
            await connection.start()

    assert websocket.closed >= 1


@pytest.mark.asyncio
async def test_connection_cleans_up_when_signalr_handshake_fails():
    websocket = MockWebSocket()
    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        websocket.incoming.put_nowait(json.dumps({"error": "handshake rejected"}) + RECORD_SEPARATOR)

        with pytest.raises(ValueError, match="handshake rejected"):
            await connection.start()

    assert websocket.closed >= 1


@pytest.mark.asyncio
async def test_connection_abort_cancels_websocket_handshake_without_late_start():
    factory_started = asyncio.Event()
    factory_cancelled = asyncio.Event()
    stop_event = asyncio.Event()

    async def blocked_factory(_: str) -> MockWebSocket:
        factory_started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            factory_cancelled.set()
            raise
        raise AssertionError("unreachable")

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(),
            http_client=client,
            websocket_factory=blocked_factory,
        )
        start = asyncio.create_task(connection.start(stop_event))
        await factory_started.wait()
        stop_event.set()

        with pytest.raises(SocketConnectionAborted):
            await start

    assert factory_cancelled.is_set()


@pytest.mark.asyncio
async def test_connection_abort_leaves_no_orphan_tasks():
    """The interruptible wait races several watcher tasks; none may outlive the call."""
    factory_started = asyncio.Event()
    stop_event = asyncio.Event()

    async def blocked_factory(_: str) -> MockWebSocket:
        factory_started.set()
        await asyncio.Future()
        raise AssertionError("unreachable")

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(),
            http_client=client,
            websocket_factory=blocked_factory,
        )
        before = {id(task) for task in asyncio.all_tasks()}
        start = asyncio.create_task(connection.start(stop_event))
        await factory_started.wait()
        # The race really is running: operation + internal stop + external stop are live.
        assert len(asyncio.all_tasks()) > len(before) + 1
        stop_event.set()

        with pytest.raises(SocketConnectionAborted):
            await start
        await asyncio.sleep(0)

        survivors = [task for task in asyncio.all_tasks() if id(task) not in before]
        assert survivors == [], [task.get_name() for task in survivors]


@pytest.mark.asyncio
async def test_connection_notifies_terminal_close_once_and_ignores_duplicate_ready():
    websocket = MockWebSocket()
    ready_count = 0
    closed: list[Optional[Exception]] = []

    def on_ready(_: SocketReadyFrame) -> None:
        nonlocal ready_count
        ready_count += 1

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(on_ready=on_ready, on_closed=closed.append),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        websocket.incoming.put_nowait(
            f"{{}}{RECORD_SEPARATOR}"
            + json.dumps({"type": 1, "target": "SocketReady", "arguments": [{}]})
            + RECORD_SEPARATOR
        )
        await connection.start()
        websocket.incoming.put_nowait(
            json.dumps({"type": 1, "target": "SocketReady", "arguments": [{}]}) + RECORD_SEPARATOR
        )
        websocket.incoming.put_nowait(ConnectionError("network drop"))
        await _eventually(lambda: len(closed) == 1)

    assert ready_count == 1
    assert isinstance(closed[0], ConnectionError)
    await connection.stop()


async def _token(value: str) -> str:
    return value


async def _websocket(value: MockWebSocket) -> MockWebSocket:
    return value


async def _eventually(predicate: Callable[[], bool], timeout: float = 1.0) -> None:
    async def poll() -> None:
        for _ in range(round(timeout / 0.001) + 1):
            if predicate():
                return
            await asyncio.sleep(0.001)
        raise TimeoutError("condition did not become true")

    await asyncio.wait_for(poll(), timeout)


@pytest.mark.asyncio
async def test_default_websocket_factory_defers_open_timeout_to_caller(monkeypatch: pytest.MonkeyPatch):
    """The connection bounds the open itself; a second timeout here would cap the configured value."""
    captured: dict[str, object] = {}

    async def fake_connect(url: str, **kwargs: object) -> object:
        captured.update(kwargs)
        return MockWebSocket()

    monkeypatch.setattr(connection_module, "connect", fake_connect)
    await connection_module._open_websocket("wss://socket.example/hub")

    assert captured["open_timeout"] is None


@pytest.mark.asyncio
async def test_default_websocket_factory_caps_frame_size(monkeypatch: pytest.MonkeyPatch):
    """The library-level cap is the first line of defence against an oversized single frame."""
    captured: dict[str, object] = {}

    async def fake_connect(url: str, **kwargs: object) -> object:
        captured.update(kwargs)
        return MockWebSocket()

    monkeypatch.setattr(connection_module, "connect", fake_connect)
    await connection_module._open_websocket("wss://socket.example/hub")

    assert captured["max_size"] == connection_module.MAX_FRAME_BYTES


@pytest.mark.asyncio
async def test_connection_rejects_a_pre_aborted_start_without_minting_a_token():
    """Stop already requested: abort before the bot token is fetched or a socket is opened."""
    side_effects: list[str] = []

    async def token() -> str:
        side_effects.append("token")
        return "bot-token"

    async def factory(_: str) -> MockWebSocket:
        side_effects.append("websocket")
        return MockWebSocket()

    connection = SignalRSocketConnection(
        SocketConnectionContext(
            negotiate_url="https://botapi.example/v3/websockets/connect",
            get_bot_token=token,
        ),
        make_handlers(),
        websocket_factory=factory,
    )
    stop = asyncio.Event()
    stop.set()

    with pytest.raises(SocketConnectionAborted):
        await connection.start(stop)

    assert side_effects == []


@pytest.mark.asyncio
async def test_readiness_survives_a_throwing_on_ready_observer():
    """A failing observer must not strand start(); readiness is resolved before it runs."""
    websocket = MockWebSocket()

    def on_ready(_: SocketReadyFrame) -> None:
        raise RuntimeError("observer exploded")

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(on_ready=on_ready),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        start = asyncio.create_task(connection.start())
        await _eventually(lambda: len(websocket.sent) == 1)
        websocket.incoming.put_nowait(f"{{}}{RECORD_SEPARATOR}")
        websocket.incoming.put_nowait(
            json.dumps({"type": 1, "target": "SocketReady", "arguments": [{}]}) + RECORD_SEPARATOR
        )

        await asyncio.wait_for(start, timeout=1.0)
        await connection.stop()


@pytest.mark.asyncio
async def test_chunk_without_record_separator_fails_closed():
    """
    Nothing is buffered across reads, so an endless separator-less stream cannot grow
    memory: the first incomplete chunk ends the connection.
    """
    websocket = MockWebSocket()
    closed: list[Optional[Exception]] = []

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(on_closed=closed.append),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        start = asyncio.create_task(connection.start())
        await _eventually(lambda: len(websocket.sent) == 1)

        websocket.incoming.put_nowait("x" * 32)

        with pytest.raises(SignalRProtocolError, match="incomplete"):
            await asyncio.wait_for(start, timeout=1.0)

        await _eventually(lambda: len(closed) == 1)
        assert websocket.closed == 1


@pytest.mark.asyncio
async def test_hub_message_split_across_reads_is_rejected():
    """
    Matches the SignalR JS client: each chunk is parsed on its own, and a half-delivered
    frame is a protocol error rather than something held back for the next read.
    """
    websocket = MockWebSocket()

    async with make_http_client() as client:
        connection = SignalRSocketConnection(
            make_context(),
            make_handlers(),
            http_client=client,
            websocket_factory=lambda _: _websocket(websocket),
        )
        start = asyncio.create_task(connection.start())
        await _eventually(lambda: len(websocket.sent) == 1)
        websocket.incoming.put_nowait(f"{{}}{RECORD_SEPARATOR}")

        ready = (
            json.dumps(
                {
                    "type": 1,
                    "target": "SocketReady",
                    "arguments": [{"botKey": "bot-1", "connectionId": "conn-1"}],
                }
            )
            + RECORD_SEPARATOR
        )
        websocket.incoming.put_nowait(ready[: len(ready) // 2])

        with pytest.raises(SignalRProtocolError, match="incomplete"):
            await asyncio.wait_for(start, timeout=1.0)
