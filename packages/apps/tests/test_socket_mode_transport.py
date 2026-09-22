"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Callable, Optional

import pytest
from microsoft_teams.apps.socket_mode.transport import (
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
