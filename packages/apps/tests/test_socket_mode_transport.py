"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Callable, Optional

import pytest
from microsoft_teams.apps.socket_mode import geo_socket
from microsoft_teams.apps.socket_mode.connection import SocketConnectionAborted
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


class MockConnection:
    def __init__(
        self,
        handlers: SocketConnectionHandlers,
        *,
        start_error: Optional[Exception] = None,
        expires_in_seconds: Optional[float] = None,
    ):
        self.handlers = handlers
        self.start_error = start_error
        self._expires_in_seconds = expires_in_seconds
        self.started = 0
        self.stopped = 0

    @property
    def expires_in_seconds(self) -> Optional[float]:
        return self._expires_in_seconds

    async def start(self, stop_event: Optional[asyncio.Event] = None) -> None:
        self.started += 1
        if stop_event is not None and stop_event.is_set():
            raise asyncio.CancelledError
        if self.start_error is not None:
            raise self.start_error
        self.handlers.on_ready(SocketReadyFrame(connection_id=f"conn-{self.started}"))

    async def stop(self) -> None:
        self.stopped += 1

    def drop(self, error: Optional[Exception] = None) -> None:
        self.handlers.on_closed(error)


class MockConnectionFactory:
    def __init__(self):
        self.connections: list[MockConnection] = []
        self.urls: list[str] = []
        self.start_errors: list[Exception] = []
        self.expires_in_seconds: Optional[float] = None

    def __call__(self, url: str, handlers: SocketConnectionHandlers) -> MockConnection:
        error = self.start_errors.pop(0) if self.start_errors else None
        connection = MockConnection(
            handlers,
            start_error=error,
            expires_in_seconds=self.expires_in_seconds,
        )
        self.urls.append(url)
        self.connections.append(connection)
        return connection


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
            on_disconnected=lambda geo, _: disconnected.append(geo),
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
            on_disconnected=lambda geo, _: disconnected.append(geo),
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
            on_disconnected=lambda geo, _: disconnected.append(geo),
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
