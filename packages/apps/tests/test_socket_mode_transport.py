"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from typing import AsyncIterator, Callable, Optional

import httpx
import pytest
from microsoft_teams.apps.socket_mode import geo_socket
from microsoft_teams.apps.socket_mode.connection import SignalRSocketConnection, SocketConnectionAborted
from microsoft_teams.apps.socket_mode.negotiate import NegotiateError
from microsoft_teams.apps.socket_mode.signalr import encode_hub_message
from microsoft_teams.apps.socket_mode.transport import (
    RECONNECT_MAX_DELAY,
    SocketModeTransport,
    SocketModeTransportOptions,
)
from microsoft_teams.apps.socket_mode.types import (
    ReplyFrame,
    SocketActivityEnvelope,
    SocketConnectionHandlers,
    SocketModeCallbacks,
    SocketModeStatus,
    SocketReadyFrame,
)
from test_socket_mode_connection import MockWebSocket


class MockConnection:
    def __init__(
        self,
        handlers: SocketConnectionHandlers,
        *,
        start_error: Optional[Exception] = None,
        start_gate: Optional[asyncio.Event] = None,
        expires_in_seconds: Optional[float] = None,
    ):
        self.handlers = handlers
        self.start_error = start_error
        self.start_gate = start_gate
        self.stop_gate: Optional[asyncio.Event] = None
        self.start_entered = asyncio.Event()
        self.stop_entered = asyncio.Event()
        self._expires_in_seconds = expires_in_seconds
        self.started = 0
        self.stopped = 0

    @property
    def expires_in_seconds(self) -> Optional[float]:
        return self._expires_in_seconds

    async def start(self, stop_event: Optional[asyncio.Event] = None) -> None:
        self.started += 1
        self.start_entered.set()
        if stop_event is not None and stop_event.is_set():
            raise asyncio.CancelledError
        if self.start_gate is not None:
            await self.start_gate.wait()
        if self.start_error is not None:
            raise self.start_error
        self.handlers.on_ready(SocketReadyFrame(connection_id=f"conn-{self.started}"))

    async def stop(self) -> None:
        self.stopped += 1
        self.stop_entered.set()
        if self.stop_gate is not None:
            await self.stop_gate.wait()

    def drop(self, error: Optional[Exception] = None) -> None:
        self.handlers.on_closed(error)


class MockConnectionFactory:
    def __init__(self):
        self.connections: list[MockConnection] = []
        self.urls: list[str] = []
        self.start_errors: list[Exception] = []
        self.start_gate: Optional[asyncio.Event] = None
        self.expires_in_seconds: Optional[float] = None

    def __call__(self, url: str, handlers: SocketConnectionHandlers) -> MockConnection:
        error = self.start_errors.pop(0) if self.start_errors else None
        connection = MockConnection(
            handlers,
            start_error=error,
            start_gate=self.start_gate,
            expires_in_seconds=self.expires_in_seconds,
        )
        self.urls.append(url)
        self.connections.append(connection)
        return connection


class GatedCloseWebSocket(MockWebSocket):
    def __init__(self):
        super().__init__()
        self.close_started = asyncio.Event()
        self.release_close = asyncio.Event()
        self.close_finished = asyncio.Event()
        self.close_cancelled = False

    async def close(self) -> None:
        self.close_started.set()
        try:
            await self.release_close.wait()
            await super().close()
            self.close_finished.set()
        except asyncio.CancelledError:
            self.close_cancelled = True
            raise


@pytest.fixture
async def gated_socket_transport() -> AsyncIterator[
    tuple[SocketModeTransport, GatedCloseWebSocket, asyncio.Queue[httpx.Response]]
]:
    websocket = GatedCloseWebSocket()
    websocket.incoming.put_nowait(
        encode_hub_message({}) + encode_hub_message({"type": 1, "target": "SocketReady", "arguments": [{}]})
    )
    responses: asyncio.Queue[httpx.Response] = asyncio.Queue()
    responses.put_nowait(
        httpx.Response(200, json={"url": "wss://signalr.example/client", "accessToken": "token", "expiresIn": 3600})
    )

    async def open_socket(_: str) -> GatedCloseWebSocket:
        return websocket

    async def on_activity(_: SocketActivityEnvelope) -> Optional[ReplyFrame]:
        return None

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: responses.get_nowait())) as client:
        transport = SocketModeTransport(
            SocketModeTransportOptions(geos=("amer",), reconnect_delays=(0,)),
            get_bot_token=lambda: _token("token"),
            on_activity=on_activity,
            http_client=client,
            websocket_factory=open_socket,
        )
        try:
            await transport.start()
            yield transport, websocket, responses
        finally:
            websocket.release_close.set()
            await transport.stop()


async def make_transport(
    factory: MockConnectionFactory,
    *,
    geos: tuple[str, ...] = ("",),
    callbacks: Optional[SocketModeCallbacks] = None,
    on_activity: Optional[Callable[[SocketActivityEnvelope], object]] = None,
    startup_timeout: float = 1,
    reconnect_delays: tuple[float, ...] = (0,),
) -> SocketModeTransport:
    async def dispatch(envelope: SocketActivityEnvelope) -> Optional[ReplyFrame]:
        if on_activity is not None:
            result = on_activity(envelope)
            if isinstance(result, ReplyFrame):
                return result
        return ReplyFrame(status=200, envelope_id=envelope.envelope_id)

    return SocketModeTransport(
        SocketModeTransportOptions(
            geos=geos,
            startup_timeout=startup_timeout,
            reconnect_delays=reconnect_delays,
        ),
        get_bot_token=lambda: _token("token"),
        on_activity=dispatch,
        callbacks=callbacks,
        connection_factory=factory,
    )


@pytest.mark.asyncio
async def test_transport_starts_all_geos_and_stops_every_connection():
    factory = MockConnectionFactory()
    transport = await make_transport(factory, geos=("amer", "emea", "apac"))

    await transport.start()

    assert transport.status == SocketModeStatus.READY
    assert factory.urls == [
        "https://botapi.skype.com/amer/v3/websockets/connect",
        "https://botapi.skype.com/emea/v3/websockets/connect",
        "https://botapi.skype.com/apac/v3/websockets/connect",
    ]
    await transport.stop()
    assert transport.status == SocketModeStatus.STOPPED
    assert all(connection.stopped >= 1 for connection in factory.connections)


@pytest.mark.asyncio
async def test_initial_connection_retries_within_startup_budget():
    factory = MockConnectionFactory()
    factory.start_errors.append(ConnectionError("negotiate unavailable"))
    transport = await make_transport(factory)

    await transport.start()

    assert len(factory.connections) == 2
    assert transport.status == SocketModeStatus.READY
    await transport.stop()


@pytest.mark.asyncio
async def test_initial_failure_exhausts_zero_retry_budget_and_cleans_up():
    factory = MockConnectionFactory()
    factory.start_errors.append(ConnectionError("negotiate unavailable"))
    transport = await make_transport(factory, startup_timeout=0)

    with pytest.raises(ConnectionError, match="negotiate unavailable"):
        await transport.start()

    assert transport.status == SocketModeStatus.STOPPED
    assert factory.connections[0].stopped >= 1


@pytest.mark.asyncio
async def test_drop_reconnects_and_fences_superseded_generation():
    factory = MockConnectionFactory()
    dispatched: list[Optional[str]] = []
    disconnected: list[str] = []
    reconnected: list[str] = []
    transport = await make_transport(
        factory,
        on_activity=lambda envelope: dispatched.append(envelope.envelope_id),
        callbacks=SocketModeCallbacks(
            on_disconnected=lambda geo, _, terminal: disconnected.append(geo),
            on_reconnected=reconnected.append,
        ),
    )
    await transport.start()
    old = factory.connections[0]

    old.drop(ConnectionError("network drop"))
    await _eventually(lambda: len(factory.connections) == 2)

    stale_reply = await old.handlers.on_activity(
        SocketActivityEnvelope(envelope_id="stale", payload={"type": "message"})
    )
    current_reply = await factory.connections[1].handlers.on_activity(
        SocketActivityEnvelope(envelope_id="current", payload={"type": "message"})
    )

    assert stale_reply is None
    assert current_reply is not None
    assert dispatched == ["current"]
    assert disconnected == [""]
    assert reconnected == [""]
    await transport.stop()


@pytest.mark.asyncio
async def test_reconnect_keeps_retrying_until_fresh_generation_is_ready():
    factory = MockConnectionFactory()
    transport = await make_transport(factory)
    await transport.start()
    factory.start_errors.append(ConnectionError("first reconnect failed"))

    factory.connections[0].drop()
    await _eventually(lambda: len(factory.connections) == 3)

    assert transport.status == SocketModeStatus.READY
    await transport.stop()


@pytest.mark.asyncio
async def test_proactive_refresh_rotates_without_disconnect_callbacks():
    factory = MockConnectionFactory()
    factory.expires_in_seconds = 0.01
    disconnected: list[str] = []
    reconnected: list[str] = []
    transport = await make_transport(
        factory,
        callbacks=SocketModeCallbacks(
            on_disconnected=lambda geo, _, terminal: disconnected.append(geo),
            on_reconnected=reconnected.append,
        ),
    )
    await transport.start()

    await _eventually(lambda: len(factory.connections) == 2, timeout=1.5)

    assert transport.status == SocketModeStatus.READY
    assert disconnected == []
    assert reconnected == []
    await transport.stop()


@pytest.mark.asyncio
async def test_stop_prevents_reconnect_after_late_close():
    factory = MockConnectionFactory()
    transport = await make_transport(factory)
    await transport.start()
    first = factory.connections[0]

    await transport.stop()
    first.drop(ConnectionError("late close"))
    await asyncio.sleep(0)

    assert len(factory.connections) == 1
    assert transport.status == SocketModeStatus.STOPPED


@pytest.mark.asyncio
async def test_transport_stop_is_idempotent_and_transport_can_restart():
    factory = MockConnectionFactory()
    transport = await make_transport(factory)
    await transport.start()

    await transport.stop()
    await transport.stop()
    await transport.start()

    assert transport.status == SocketModeStatus.READY
    assert len(factory.connections) == 2
    await transport.stop()


def test_reconnect_schedule_caps_at_last_configured_delay():
    factory = MockConnectionFactory()
    transport = SocketModeTransport(
        SocketModeTransportOptions(geos=("",), reconnect_delays=(0.25, 0.5)),
        get_bot_token=lambda: _token("token"),
        on_activity=lambda _: _reply(),
        connection_factory=factory,
    )

    assert transport.backoff_delay(0) == 0.25
    assert transport.backoff_delay(1) == 0.5
    assert transport.backoff_delay(10) == 0.5


def test_exponential_backoff_survives_a_long_failure_streak():
    """Without a clamp on the exponent, ``2**attempt`` overflows the float conversion."""
    factory = MockConnectionFactory()
    transport = SocketModeTransport(
        SocketModeTransportOptions(geos=("",), reconnect_delays=()),
        get_bot_token=lambda: _token("token"),
        on_activity=lambda _: _reply(),
        connection_factory=factory,
    )

    for attempt in (1023, 1024, 100_000):
        assert 0.0 <= transport.backoff_delay(attempt) <= RECONNECT_MAX_DELAY


async def _token(value: str) -> str:
    return value


async def _reply() -> ReplyFrame:
    return ReplyFrame(status=200)


async def _eventually(predicate: Callable[[], bool], timeout: float = 1.0) -> None:
    async def poll() -> None:
        for _ in range(round(timeout / 0.001) + 1):
            if predicate():
                return
            await asyncio.sleep(0.001)
        raise TimeoutError("condition did not become true")

    await asyncio.wait_for(poll(), timeout)


class _BlockingConnection(MockConnection):
    """Blocks in start() the way a real connection blocks in negotiate or readiness."""

    def __init__(
        self,
        handlers: SocketConnectionHandlers,
        *,
        entered: asyncio.Event,
        honour_stop: bool,
    ):
        super().__init__(handlers)
        self._entered = entered
        self._honour_stop = honour_stop

    async def start(self, stop_event: Optional[asyncio.Event] = None) -> None:
        self.started += 1
        self._entered.set()
        if self._honour_stop and stop_event is not None:
            await stop_event.wait()
            raise SocketConnectionAborted("Socket Mode connect aborted")
        await asyncio.sleep(30)


class _BlockingFactory:
    def __init__(self, *, honour_stop: bool):
        self.connections: list[_BlockingConnection] = []
        self.entered = asyncio.Event()
        self._honour_stop = honour_stop

    def __call__(self, url: str, handlers: SocketConnectionHandlers) -> _BlockingConnection:
        connection = _BlockingConnection(handlers, entered=self.entered, honour_stop=self._honour_stop)
        self.connections.append(connection)
        return connection


@pytest.mark.asyncio
async def test_stop_interrupts_a_start_that_is_still_connecting():
    """stop() must not queue behind the startup it is cancelling."""
    factory = _BlockingFactory(honour_stop=True)
    transport = await make_transport(factory, startup_timeout=30)  # type: ignore[arg-type]

    start_task = asyncio.create_task(transport.start())
    await asyncio.wait_for(factory.entered.wait(), timeout=1)

    await asyncio.wait_for(transport.stop(), timeout=1)

    assert transport.status == SocketModeStatus.STOPPED
    with pytest.raises(SocketConnectionAborted):
        await start_task


@pytest.mark.asyncio
async def test_startup_budget_bounds_an_attempt_that_outlives_it():
    """A single attempt's per-step timeouts can exceed the budget, so the budget caps it."""
    factory = _BlockingFactory(honour_stop=False)
    transport = await make_transport(factory, startup_timeout=0.05)  # type: ignore[arg-type]

    started = asyncio.get_running_loop().time()
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(transport.start(), timeout=5)
    elapsed = asyncio.get_running_loop().time() - started

    assert elapsed < 2
    assert transport.status == SocketModeStatus.STOPPED


class _FailThenHangConnection(MockConnection):
    """First attempt fails with a diagnosable error; the next one outlives the budget."""

    def __init__(self, handlers: SocketConnectionHandlers, *, attempts: list[int]):
        super().__init__(handlers)
        self._attempts = attempts

    async def start(self, stop_event: Optional[asyncio.Event] = None) -> None:
        self.started += 1
        self._attempts.append(1)
        if len(self._attempts) == 1:
            raise ConnectionError("negotiate returned HTTP 503")
        await asyncio.sleep(30)


@pytest.mark.asyncio
async def test_startup_budget_cutoff_keeps_the_error_that_explains_the_failure():
    """A budget cut-off is not a diagnosis, so it must not mask the real failure."""
    attempts: list[int] = []

    def factory(url: str, handlers: SocketConnectionHandlers) -> _FailThenHangConnection:
        return _FailThenHangConnection(handlers, attempts=attempts)

    transport = await make_transport(factory, startup_timeout=0.2)  # type: ignore[arg-type]

    with pytest.raises(ConnectionError, match="negotiate returned HTTP 503"):
        await asyncio.wait_for(transport.start(), timeout=5)

    assert len(attempts) >= 2, "the budget should have allowed a retry after the first failure"
    assert transport.status == SocketModeStatus.STOPPED


async def _dispatch(connection: MockConnection, envelope_id: str) -> Optional[ReplyFrame]:
    return await connection.handlers.on_activity(
        SocketActivityEnvelope(envelope_id=envelope_id, payload={"type": "message"})
    )


@pytest.mark.asyncio
async def test_planned_rotation_keeps_the_previous_connection_serving(monkeypatch: pytest.MonkeyPatch):
    # Long enough that the handoff is still open while the assertions run.
    monkeypatch.setattr(geo_socket, "CONNECTION_HANDOFF_SECONDS", 30.0)
    factory = MockConnectionFactory()
    factory.expires_in_seconds = 0.01
    dispatched: list[Optional[str]] = []
    transport = await make_transport(factory, on_activity=lambda envelope: dispatched.append(envelope.envelope_id))
    await transport.start()
    previous = factory.connections[0]

    await _eventually(lambda: len(factory.connections) == 2, timeout=1.5)

    # The service can still be routing to the old connection id, so it must keep working.
    assert previous.stopped == 0
    assert await _dispatch(previous, "during-handoff") is not None
    assert await _dispatch(factory.connections[1], "on-replacement") is not None
    assert dispatched == ["during-handoff", "on-replacement"]
    assert transport.status == SocketModeStatus.READY
    await transport.stop()


@pytest.mark.asyncio
async def test_retired_connection_closes_and_stops_dispatching_after_the_handoff(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(geo_socket, "CONNECTION_HANDOFF_SECONDS", 0.01)
    factory = MockConnectionFactory()
    factory.expires_in_seconds = 0.01
    transport = await make_transport(factory)
    await transport.start()
    previous = factory.connections[0]

    await _eventually(lambda: len(factory.connections) == 2, timeout=1.5)
    await _eventually(lambda: previous.stopped >= 1, timeout=1.5)

    assert await _dispatch(previous, "after-handoff") is None
    assert await _dispatch(factory.connections[1], "current") is not None
    await transport.stop()


@pytest.mark.asyncio
async def test_rotation_whose_predecessor_dies_early_reports_a_disconnect(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(geo_socket, "CONNECTION_HANDOFF_SECONDS", 30.0)
    factory = MockConnectionFactory()
    factory.expires_in_seconds = 0.01
    disconnected: list[str] = []
    reconnected: list[str] = []
    transport = await make_transport(
        factory,
        callbacks=SocketModeCallbacks(
            on_disconnected=lambda geo, _, terminal: disconnected.append(geo),
            on_reconnected=reconnected.append,
        ),
        # Hold the replacement back so the predecessor is still the only live socket.
        reconnect_delays=(0.2,),
    )
    await transport.start()
    previous = factory.connections[0]
    geo = transport._geos[0]

    # Kill the predecessor strictly between the planned close and its replacement being
    # created, which is the only window where the rotation has no other live socket.
    def rotation_in_flight() -> bool:
        closed = geo._closed
        return closed is not None and closed.done() and len(factory.connections) == 1

    await _eventually(rotation_in_flight, timeout=1.5)
    previous.drop(ConnectionError("died mid-rotation"))

    await _eventually(lambda: disconnected == [""], timeout=2.0)
    await _eventually(lambda: reconnected == [""], timeout=2.0)
    assert transport.status == SocketModeStatus.READY
    await transport.stop()


@pytest.mark.asyncio
async def test_stop_closes_connections_still_inside_the_handoff_window(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(geo_socket, "CONNECTION_HANDOFF_SECONDS", 30.0)
    factory = MockConnectionFactory()
    factory.expires_in_seconds = 0.01
    transport = await make_transport(factory)
    await transport.start()
    previous = factory.connections[0]

    await _eventually(lambda: len(factory.connections) == 2, timeout=1.5)
    assert previous.stopped == 0

    await transport.stop()

    # A retiring connection is still owned, so shutdown must not leak it.
    assert previous.stopped >= 1
    assert factory.connections[1].stopped >= 1


@pytest.mark.asyncio
async def test_startup_retry_waits_for_retry_after_instead_of_its_own_backoff():
    """A throttled negotiate must be obeyed; retrying on the local backoff would amplify it."""
    factory = MockConnectionFactory()
    factory.start_errors.append(NegotiateError("throttled", retry_after=0.25))
    # Backoff alone would retry immediately, so any real wait has to come from Retry-After.
    transport = await make_transport(factory, startup_timeout=2, reconnect_delays=(0,))

    started = asyncio.get_running_loop().time()
    await transport.start()
    elapsed = asyncio.get_running_loop().time() - started

    assert transport.status == SocketModeStatus.READY
    assert len(factory.connections) == 2
    assert elapsed >= 0.25

    await transport.stop()


@pytest.mark.asyncio
async def test_overlapping_predecessors_each_serve_their_own_handoff(monkeypatch: pytest.MonkeyPatch):
    """Rotations can overlap, so retirement must be per-generation rather than one shared slot."""
    monkeypatch.setattr(geo_socket, "CONNECTION_HANDOFF_SECONDS", 30.0)
    factory = MockConnectionFactory()
    factory.expires_in_seconds = 0.01
    dispatched: list[Optional[str]] = []
    transport = await make_transport(factory, on_activity=lambda envelope: dispatched.append(envelope.envelope_id))
    await transport.start()

    # Every connection expires, so a second rotation begins while the first is still retiring.
    await _eventually(lambda: len(factory.connections) == 3, timeout=5.0)

    first, second, current = factory.connections[0], factory.connections[1], factory.connections[2]
    assert first.stopped == 0
    assert second.stopped == 0

    assert await _dispatch(first, "oldest") is not None
    assert await _dispatch(second, "middle") is not None
    assert await _dispatch(current, "current") is not None
    assert dispatched == ["oldest", "middle", "current"]

    await transport.stop()

    assert first.stopped >= 1
    assert second.stopped >= 1
    assert current.stopped >= 1


@pytest.mark.asyncio
async def test_terminal_negotiate_failure_is_not_retried_during_startup():
    factory = MockConnectionFactory()
    factory.start_errors.append(NegotiateError("Socket Mode negotiate failed: HTTP 403", terminal=True))
    transport = await make_transport(factory, startup_timeout=5)

    with pytest.raises(NegotiateError, match="HTTP 403"):
        await transport.start()

    assert len(factory.connections) == 1
    assert factory.connections[0].stopped >= 1
    assert transport.status == SocketModeStatus.STOPPED


@pytest.mark.asyncio
async def test_terminal_negotiate_failure_stops_the_reconnect_loop(caplog: pytest.LogCaptureFixture):
    factory = MockConnectionFactory()
    rejected = NegotiateError("Socket Mode negotiate failed: HTTP 401", terminal=True)
    errors: list[Optional[Exception]] = []
    transport = await make_transport(
        factory, callbacks=SocketModeCallbacks(on_disconnected=lambda _, error, terminal: errors.append(error))
    )
    await transport.start()
    factory.start_errors.append(rejected)

    factory.connections[0].drop(ConnectionError("network drop"))
    await _eventually(lambda: rejected in errors)

    await asyncio.sleep(0.05)
    assert len(factory.connections) == 2
    assert transport.status == SocketModeStatus.DISCONNECTED
    assert all(connection.stopped >= 1 for connection in factory.connections)
    await transport.stop()
    assert sum("inbound delivery paused" in record.message for record in caplog.records) == 1
    assert sum(record.levelno == logging.ERROR for record in caplog.records) == 1
    assert "stopped until the app is restarted" in caplog.text


@pytest.mark.asyncio
async def test_terminal_refresh_failure_closes_only_the_affected_geo(caplog: pytest.LogCaptureFixture):
    factory = MockConnectionFactory()
    rejected = NegotiateError("Socket Mode negotiate failed: HTTP 403", terminal=True)
    errors: list[tuple[str, Optional[Exception]]] = []
    transport = await make_transport(
        factory,
        geos=("amer", "emea"),
        callbacks=SocketModeCallbacks(on_disconnected=lambda geo, error, terminal: errors.append((geo, error))),
    )
    await transport.start()
    affected, healthy = factory.connections
    geo = transport._geos[0]
    closed = geo._closed
    assert closed is not None
    factory.start_errors.append(rejected)
    geo._schedule_refresh(1, 0.01, closed)

    await _eventually(lambda: ("amer", rejected) in errors, timeout=1.5)

    assert affected.stopped >= 1
    assert healthy.stopped == 0
    assert dict(transport.geo_statuses) == {"amer": SocketModeStatus.DISCONNECTED, "emea": SocketModeStatus.READY}
    assert await _dispatch(affected, "after-rejection") is None
    assert await _dispatch(healthy, "still-serving") is not None
    assert len(factory.connections) == 3
    await transport.stop()
    assert "inbound delivery paused" not in caplog.text
    assert sum(record.levelno == logging.ERROR for record in caplog.records) == 1


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.asyncio
async def test_shutdown_suppresses_late_negotiate_rejection(status: int, caplog: pytest.LogCaptureFixture):
    factory = MockConnectionFactory()
    events: list[tuple[object, ...]] = []
    transport = await make_transport(
        factory, callbacks=SocketModeCallbacks(on_disconnected=lambda *args: events.append(args))
    )
    await transport.start()
    first = factory.connections[0]
    first.stop_gate = asyncio.Event()
    factory.start_gate = asyncio.Event()
    factory.start_errors.append(NegotiateError(f"HTTP {status}", terminal=True))
    geo = transport._geos[0]
    closed, supervisor = geo._closed, geo._supervisor
    assert closed is not None and supervisor is not None
    closed.set_result(geo_socket._CloseReason(planned=True))
    await _eventually(lambda: len(factory.connections) == 2)
    await asyncio.wait_for(factory.connections[1].start_entered.wait(), 1)

    stopping = asyncio.create_task(transport.stop())
    try:
        await asyncio.wait_for(first.stop_entered.wait(), 1)
        factory.start_gate.set()
        await asyncio.wait_for(asyncio.shield(supervisor), 1)
    finally:
        first.stop_gate.set()
        await asyncio.wait_for(stopping, 1)

    assert events == []
    assert caplog.records == []
    assert transport.status == SocketModeStatus.STOPPED
    assert len(factory.connections) == 2


@pytest.mark.asyncio
async def test_shutdown_during_terminal_cleanup_suppresses_outage(caplog: pytest.LogCaptureFixture):
    factory = MockConnectionFactory()
    events: list[tuple[object, ...]] = []
    transport = await make_transport(
        factory, callbacks=SocketModeCallbacks(on_disconnected=lambda *args: events.append(args))
    )
    await transport.start()
    first = factory.connections[0]
    first.stop_gate = asyncio.Event()
    factory.start_errors.append(NegotiateError("HTTP 403", terminal=True))
    closed = transport._geos[0]._closed
    assert closed is not None
    closed.set_result(geo_socket._CloseReason(planned=True))
    await asyncio.wait_for(first.stop_entered.wait(), 1)
    assert events == []

    stopping = asyncio.create_task(transport.stop())
    # Queue stop before releasing cleanup: its stop flag wins before the supervisor resumes.
    first.stop_gate.set()
    await asyncio.wait_for(stopping, 1)

    assert events == []
    assert transport.status == SocketModeStatus.STOPPED
    assert sum(record.levelno == logging.ERROR for record in caplog.records) == 1
    assert "inbound delivery paused" not in caplog.text


@pytest.mark.asyncio
async def test_terminal_refresh_closes_active_and_retiring_connections(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(geo_socket, "CONNECTION_HANDOFF_SECONDS", 60)
    factory = MockConnectionFactory()
    events: list[tuple[object, ...]] = []
    transport = await make_transport(
        factory,
        geos=("amer", "emea"),
        callbacks=SocketModeCallbacks(on_disconnected=lambda *args: events.append(args)),
    )
    await transport.start()
    first, healthy = factory.connections
    factory.expires_in_seconds = 0.01
    geo = transport._geos[0]
    closed = geo._closed
    assert closed is not None
    closed.set_result(geo_socket._CloseReason(planned=True))
    try:
        await _eventually(lambda: len(factory.connections) == 3 and bool(geo._retire_tasks))
        active = factory.connections[2]
        rejected = NegotiateError("HTTP 403", terminal=True)
        factory.start_errors.append(rejected)
        await _eventually(lambda: bool(events), timeout=1.5)

        assert events == [("amer", rejected, True)]
        assert first.stopped >= 1
        assert active.stopped >= 1
        assert healthy.stopped == 0
        assert geo._retiring == {}
        assert not geo._retire_tasks
        assert await _dispatch(first, "retired-after-rejection") is None
        assert await _dispatch(active, "active-after-rejection") is None
        assert await _dispatch(healthy, "still-serving") is not None
    finally:
        await transport.stop()


@pytest.mark.parametrize("status", [401, 403])
@pytest.mark.asyncio
async def test_terminal_geo_cleanup_survives_concurrent_transport_stop(
    gated_socket_transport: tuple[SocketModeTransport, GatedCloseWebSocket, asyncio.Queue[httpx.Response]],
    status: int,
):
    transport, websocket, responses = gated_socket_transport
    events: list[tuple[object, ...]] = []
    transport._callbacks = SocketModeCallbacks(on_disconnected=lambda *args: events.append(args))
    geo = transport._geos[0]
    active, closed, supervisor = geo._active, geo._closed, geo._supervisor
    assert active is not None and closed is not None and supervisor is not None
    assert isinstance(active.connection, SignalRSocketConnection)
    listener, heartbeat = active.connection._listener, active.connection._heartbeat
    assert listener is not None and heartbeat is not None
    responses.put_nowait(httpx.Response(status))
    closed.set_result(geo_socket._CloseReason(planned=True))
    await asyncio.wait_for(websocket.close_started.wait(), 1)

    stopping = asyncio.create_task(transport.stop())
    try:
        done, _ = await asyncio.wait((stopping,), timeout=0.05)
        assert not done, "Transport shutdown returned before websocket.close completed"
        assert not websocket.close_cancelled
    finally:
        websocket.release_close.set()
        await asyncio.wait_for(stopping, 1)

    assert websocket.close_finished.is_set()
    assert websocket.closed == 1
    assert not websocket.close_cancelled
    assert listener.done() and heartbeat.done() and supervisor.done()
    assert events == []
    assert transport.status == SocketModeStatus.STOPPED


@pytest.mark.asyncio
async def test_cancelled_stop_waiter_does_not_cancel_shared_socket_cleanup(
    gated_socket_transport: tuple[SocketModeTransport, GatedCloseWebSocket, asyncio.Queue[httpx.Response]],
):
    transport, websocket, _ = gated_socket_transport
    first_stop = asyncio.create_task(transport.stop())
    await asyncio.wait_for(websocket.close_started.wait(), 1)
    first_stop.cancel()
    with pytest.raises(asyncio.CancelledError):
        await first_stop

    second_stop = asyncio.create_task(transport.stop())
    try:
        done, _ = await asyncio.wait((second_stop,), timeout=0.05)
        assert not done, "A second stop skipped the cancelled caller's pending cleanup"
        assert not websocket.close_cancelled
    finally:
        websocket.release_close.set()
        await asyncio.wait_for(second_stop, 1)

    assert websocket.close_finished.is_set()
    assert websocket.closed == 1
    assert not websocket.close_cancelled
    assert transport.status == SocketModeStatus.STOPPED
