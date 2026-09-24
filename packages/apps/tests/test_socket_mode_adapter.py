"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Any, Optional

import pytest
from microsoft_teams.api import InvokeResponse, TokenProtocol
from microsoft_teams.api.auth.cloud_environment import US_GOV
from microsoft_teams.apps import App, FastAPIAdapter
from microsoft_teams.apps.events import ActivityEvent
from microsoft_teams.apps.socket_mode.adapter import SocketModeAdapter, SocketModeOptions
from microsoft_teams.apps.socket_mode.types import (
    SOCKET_MODE_PROTOCOL_VERSION,
    SocketActivityEnvelope,
    SocketModeStatus,
)
from test_socket_mode_transport import MockConnection, MockConnectionFactory

MESSAGE_ACTIVITY = {
    "type": "message",
    "id": "activity-1",
    "text": "hello",
    "serviceUrl": "https://smba.trafficmanager.net/teams",
    "from": {"id": "user-1"},
    "conversation": {"id": "conv-1"},
    "recipient": {"id": "bot-1"},
}

INVOKE_ACTIVITY = {**MESSAGE_ACTIVITY, "type": "invoke", "name": "task/fetch"}


class RecordingPipeline:
    """Stands in for the App's activity pipeline, capturing what the adapter hands it."""

    def __init__(self, response: Optional[InvokeResponse[Any]] = None, error: Optional[Exception] = None):
        self.response = response if response is not None else InvokeResponse(status=200)
        self.error = error
        self.events: list[ActivityEvent] = []

    async def __call__(self, event: ActivityEvent) -> InvokeResponse[Any]:
        self.events.append(event)
        if self.error is not None:
            raise self.error
        return self.response


async def _app_token() -> Optional[TokenProtocol]:
    return None


def make_adapter(
    factory: Optional[MockConnectionFactory] = None,
    *,
    pipeline: Optional[RecordingPipeline] = None,
    client_id: Optional[str] = "bot-client-id",
    on_error: Any = None,
    geos: tuple[str, ...] = ("",),
) -> tuple[SocketModeAdapter, RecordingPipeline]:
    pipeline = pipeline or RecordingPipeline()
    adapter = SocketModeAdapter(
        SocketModeOptions(geos=geos, startup_timeout=1, reconnect_delays=(0,)),
        process_activity=pipeline,
        get_app_token=_app_token,
        client_id=client_id,
        on_error=on_error,
        connection_factory=factory,
    )
    return adapter, pipeline


async def _start(adapter: SocketModeAdapter) -> asyncio.Task[None]:
    """Start the adapter in the background, since start() serves until stopped."""
    task = asyncio.create_task(adapter.start(0))
    for _ in range(200):
        if adapter.status == SocketModeStatus.READY:
            return task
        await asyncio.sleep(0)
    task.cancel()
    raise AssertionError("adapter never reached ready")


def envelope(activity: object, **fields: object) -> SocketActivityEnvelope:
    return SocketActivityEnvelope.model_validate({"envelopeId": "env-1", "payload": activity, **fields})


async def dispatch(connection: MockConnection, env: SocketActivityEnvelope):
    return await connection.handlers.on_activity(env)


@pytest.mark.asyncio
async def test_invoke_reply_carries_handler_status_and_body():
    factory = MockConnectionFactory()
    adapter, pipeline = make_adapter(factory, pipeline=RecordingPipeline(InvokeResponse(status=201, body={"ok": True})))
    task = await _start(adapter)

    reply = await dispatch(factory.connections[0], envelope(INVOKE_ACTIVITY, type="invoke"))

    assert reply is not None
    assert reply.status == 201
    # The handler's body is forwarded untouched; the adapter never reshapes a result.
    assert reply.body is pipeline.response.body
    assert reply.envelope_id == "env-1"
    assert reply.bot_key == "bot-client-id"
    assert reply.protocol_version == SOCKET_MODE_PROTOCOL_VERSION
    assert len(pipeline.events) == 1

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_one_way_activity_is_acknowledged_without_a_body():
    """An ack carries status only: a one-way activity has no result for the service to route."""
    factory = MockConnectionFactory()
    adapter, _ = make_adapter(factory, pipeline=RecordingPipeline(InvokeResponse(status=200, body={"leaked": True})))
    task = await _start(adapter)

    reply = await dispatch(factory.connections[0], envelope(MESSAGE_ACTIVITY))

    assert reply is not None
    assert reply.status == 200
    assert reply.body is None

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_reply_timestamps_span_the_time_the_handler_held_the_envelope():
    """``recv_at`` is stamped on arrival and ``ts`` on reply, so their gap is the bot's own latency."""

    class SlowPipeline(RecordingPipeline):
        async def __call__(self, event: ActivityEvent) -> InvokeResponse[Any]:
            await asyncio.sleep(0.05)
            return await super().__call__(event)

    factory = MockConnectionFactory()
    adapter, _ = make_adapter(factory, pipeline=SlowPipeline())
    task = await _start(adapter)

    reply = await dispatch(factory.connections[0], envelope(MESSAGE_ACTIVITY))

    assert reply is not None
    assert reply.recv_at is not None and reply.ts is not None
    assert reply.recv_at <= reply.ts
    # Stamping recv_at at reply time instead would collapse this to zero.
    assert reply.ts - reply.recv_at >= 25

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_newer_protocol_version_is_rejected_before_the_handler_runs():
    factory = MockConnectionFactory()
    adapter, pipeline = make_adapter(factory)
    task = await _start(adapter)

    reply = await dispatch(
        factory.connections[0],
        envelope(INVOKE_ACTIVITY, type="invoke", protocolVersion=SOCKET_MODE_PROTOCOL_VERSION + 1),
    )

    assert reply is not None
    assert reply.status == 400
    assert pipeline.events == []

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_absent_or_older_protocol_version_is_accepted():
    factory = MockConnectionFactory()
    adapter, pipeline = make_adapter(factory)
    task = await _start(adapter)

    assert (await dispatch(factory.connections[0], envelope(MESSAGE_ACTIVITY))) is not None
    assert (await dispatch(factory.connections[0], envelope(MESSAGE_ACTIVITY, protocolVersion=0))) is not None
    assert len(pipeline.events) == 2

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_envelope_without_an_activity_is_dropped_with_no_reply():
    factory = MockConnectionFactory()
    adapter, pipeline = make_adapter(factory)
    task = await _start(adapter)

    assert (await dispatch(factory.connections[0], envelope(None))) is None
    assert pipeline.events == []

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_handler_failure_replies_500_and_reports_the_error():
    reported: list[Exception] = []
    factory = MockConnectionFactory()
    adapter, _ = make_adapter(
        factory,
        pipeline=RecordingPipeline(error=RuntimeError("handler blew up")),
        on_error=reported.append,
    )
    task = await _start(adapter)

    reply = await dispatch(factory.connections[0], envelope(INVOKE_ACTIVITY, type="invoke"))

    assert reply is not None
    assert reply.status == 500
    assert reply.body == {"error": "bot handler error"}
    assert [str(error) for error in reported] == ["handler blew up"]

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_a_failing_error_hook_does_not_break_the_reply():
    def explode(_: Exception) -> None:
        raise ValueError("hook is broken")

    factory = MockConnectionFactory()
    adapter, _ = make_adapter(
        factory, pipeline=RecordingPipeline(error=RuntimeError("handler blew up")), on_error=explode
    )
    task = await _start(adapter)

    reply = await dispatch(factory.connections[0], envelope(INVOKE_ACTIVITY, type="invoke"))

    assert reply is not None
    assert reply.status == 500

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_synthesized_token_identifies_the_bot_without_carrying_a_credential():
    factory = MockConnectionFactory()
    adapter, pipeline = make_adapter(factory)
    task = await _start(adapter)

    await dispatch(factory.connections[0], envelope(MESSAGE_ACTIVITY))
    token = pipeline.events[0].token

    assert token.app_id == "bot-client-id"
    assert token.service_url == "https://smba.trafficmanager.net/teams"
    assert token.from_ == "azure"
    assert token.is_expired() is False
    # Never a bearer token: anything that forwards it must send nothing rather than a
    # value that looks like a credential.
    assert str(token) == ""

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_missing_app_token_is_an_explicit_error():
    adapter, _ = make_adapter()

    with pytest.raises(RuntimeError, match="could not acquire a Bot Framework app token"):
        await adapter._acquire_bot_token()


@pytest.mark.asyncio
async def test_start_serves_until_stopped():
    """
    The App awaits the adapter for the process lifetime, exactly as it awaits an HTTP
    server. Returning once the sockets were up would end App.start() and tear the loop
    down underneath them.
    """
    factory = MockConnectionFactory()
    adapter, _ = make_adapter(factory)
    task = await _start(adapter)

    # Enough turns that a start() which merely connected would have finished by now.
    for _ in range(50):
        await asyncio.sleep(0)
    assert not task.done()

    await adapter.stop()
    await asyncio.wait_for(task, timeout=1)
    assert adapter.status == SocketModeStatus.STOPPED


@pytest.mark.asyncio
async def test_lifecycle_events_are_forwarded_per_geo():
    ready: list[Any] = []
    disconnected: list[Any] = []
    reconnected: list[Any] = []

    factory = MockConnectionFactory()
    adapter, _ = make_adapter(factory, geos=("amer",))
    adapter.events.on("ready", ready.append)
    adapter.events.on("disconnected", disconnected.append)
    adapter.events.on("reconnected", reconnected.append)

    task = await _start(adapter)
    assert [event.geo for event in ready] == ["amer"]

    factory.connections[0].drop(RuntimeError("socket dropped"))
    for _ in range(200):
        if reconnected:
            break
        await asyncio.sleep(0)

    assert [event.geo for event in disconnected] == ["amer"]
    assert str(disconnected[0].error) == "socket dropped"
    assert [event.geo for event in reconnected] == ["amer"]

    await adapter.stop()
    await task


@pytest.mark.asyncio
async def test_status_and_geo_statuses_track_the_transport():
    factory = MockConnectionFactory()
    adapter, _ = make_adapter(factory, geos=("amer", "emea"))

    assert adapter.status == SocketModeStatus.IDLE
    assert adapter.geo_list == ("amer", "emea")

    task = await _start(adapter)
    assert adapter.status == SocketModeStatus.READY
    assert adapter.geo_statuses == (("amer", SocketModeStatus.READY), ("emea", SocketModeStatus.READY))

    await adapter.stop()
    await task
    assert adapter.status == SocketModeStatus.STOPPED


def test_negotiate_url_resolves_the_first_geo():
    adapter, _ = make_adapter(geos=("amer", "emea"))
    assert adapter.negotiate_url == "https://botapi.skype.com/amer/v3/websockets/connect"


def test_messaging_route_is_accepted_and_other_routes_warn(caplog: pytest.LogCaptureFixture):
    adapter, _ = make_adapter()

    async def handler(request: Any) -> Any:  # pragma: no cover - never invoked
        raise AssertionError("socket mode must not serve HTTP routes")

    with caplog.at_level("WARNING"):
        adapter.register_route("POST", "/api/messages", handler)
    assert caplog.records == []

    with caplog.at_level("WARNING"):
        adapter.register_route("POST", "/api/functions/echo", handler)
    assert "ignoring POST /api/functions/echo" in caplog.text


def test_serve_static_warns(caplog: pytest.LogCaptureFixture):
    adapter, _ = make_adapter()
    with caplog.at_level("WARNING"):
        adapter.serve_static("/tabs", "./public")
    assert "serve_static" in caplog.text


def test_options_map_onto_transport_options():
    options = SocketModeOptions(
        negotiate_base_url="https://canary.botapi.skype.com",
        geos=("amer",),
        readiness_timeout=5,
        startup_timeout=6,
        reconnect_delays=(1, 2),
        keep_alive_interval=7,
        server_timeout=8,
    )
    transport_options = options.to_transport_options()

    assert transport_options.negotiate_base_url == "https://canary.botapi.skype.com"
    assert transport_options.geos == ("amer",)
    assert transport_options.readiness_timeout == 5
    assert transport_options.startup_timeout == 6
    assert transport_options.reconnect_delays == (1, 2)
    assert transport_options.keep_alive_interval == 7
    assert transport_options.server_timeout == 8


def test_app_without_socket_mode_keeps_the_http_server():
    app = App(client_id="client", client_secret="secret", tenant_id="tenant")

    assert app.socket_mode is None
    assert isinstance(app.server.adapter, FastAPIAdapter)


def test_app_with_socket_mode_swaps_the_inbound_transport():
    app = App(client_id="client", client_secret="secret", tenant_id="tenant", socket_mode=True)

    assert isinstance(app.socket_mode, SocketModeAdapter)
    # The App drives one server; enabling Socket Mode replaces what that server is,
    # rather than running a second ingress alongside it.
    assert app.server.adapter is app.socket_mode


def test_app_socket_mode_options_are_honoured():
    app = App(
        client_id="client",
        client_secret="secret",
        tenant_id="tenant",
        socket_mode=SocketModeOptions(negotiate_base_url="https://canary.botapi.skype.com", geos=("amer",)),
    )

    assert app.socket_mode is not None
    assert app.socket_mode.geo_list == ("amer",)
    assert app.socket_mode.negotiate_url == "https://canary.botapi.skype.com/amer/v3/websockets/connect"


def test_app_rejects_socket_mode_with_a_custom_http_adapter():
    with pytest.raises(ValueError, match="mutually exclusive"):
        App(
            client_id="client",
            client_secret="secret",
            tenant_id="tenant",
            socket_mode=True,
            http_server_adapter=FastAPIAdapter(),
        )


def test_app_rejects_socket_mode_outside_the_public_cloud():
    with pytest.raises(ValueError, match="not supported in this cloud environment"):
        App(client_id="client", client_secret="secret", tenant_id="tenant", socket_mode=True, cloud=US_GOV)


def test_app_socket_mode_false_is_off():
    app = App(client_id="client", client_secret="secret", tenant_id="tenant", socket_mode=False)
    assert app.socket_mode is None
