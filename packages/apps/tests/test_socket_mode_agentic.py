"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import json
from dataclasses import replace
from unittest.mock import AsyncMock

import httpx
import pytest
from microsoft_teams.api import InvokeResponse
from microsoft_teams.apps import App, SocketModeOptions
from microsoft_teams.apps.events import ActivityEvent
from microsoft_teams.apps.socket_mode.adapter import SocketModeAdapter
from microsoft_teams.apps.socket_mode.signalr import encode_hub_message
from microsoft_teams.apps.socket_mode.types import SocketActivityEnvelope
from test_socket_mode_connection import MockWebSocket

BLUEPRINT = "blueprint"
TENANT = "connection-tenant"
SCOPE = "https://backend-agreed.example/.default"
SERVICE = "https://outbound.example/teams"
HTTPX_SEND = httpx.AsyncClient.send


def options(**kwargs):
    return SocketModeOptions(
        geos=("amer",),
        reconnect_delays=(0,),
        agentic_app_id="connection-instance",
        agentic_token_scope=SCOPE,
        **kwargs,
    )


def recipient(suffix="1"):
    return {
        "id": f"au-{suffix}",
        "role": "agenticUser",
        "agenticAppBlueprintId": BLUEPRINT,
        "agenticAppId": f"instance-{suffix}",
        "agenticUserId": f"user-{suffix}",
        "tenantId": f"tenant-{suffix}",
    }


def envelope(suffix="1", **kwargs):
    return SocketActivityEnvelope.model_validate(
        {
            "envelopeId": suffix,
            "botKey": BLUEPRINT,
            "payload": {
                "type": "message",
                "id": f"activity-{suffix}",
                "text": "hello",
                "serviceUrl": SERVICE,
                "channelId": "msteams",
                "from": {"id": "human"},
                "conversation": {"id": f"conversation-{suffix}", "conversationType": "personal"},
                "recipient": recipient(suffix),
            },
            **kwargs,
        }
    )


@pytest.fixture
async def app_state(monkeypatch):
    for key in ("CLIENT_ID", "CLIENT_SECRET", "TENANT_ID", "CLOUD", "SERVICE_URL", "OAUTH_CONNECTION_NAME"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    requests = []

    async def send(_client, request, **kwargs):
        requests.append((str(request.url), request.headers.get("authorization"), json.loads(request.content)))
        return httpx.Response(200, json={"id": f"reply-{len(requests)}"}, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    app = App(
        client_id=BLUEPRINT,
        client_secret="fake-secret",
        tenant_id=TENANT,
        fetch_user_token=False,
        socket_mode=options(),
    )
    classic = AsyncMock(side_effect=AssertionError("Must not use classic authentication"))
    agent = AsyncMock(side_effect=lambda *_: f"instance-token-{agent.await_count}")

    async def user_token(scope, app_id, user_id, tenant_id):
        await asyncio.sleep(0)
        return f"{tenant_id}:{app_id}:{user_id}"

    user = AsyncMock(side_effect=user_token)
    monkeypatch.setattr(app.token_provider, "get_app_token", classic)
    monkeypatch.setattr(app.token_provider, "get_agentic_app_token", agent)
    monkeypatch.setattr(app.token_provider, "get_agentic_user_token", user)
    await app.initialize()
    try:
        yield app, requests, classic, agent, user
    finally:
        await app.stop()


@pytest.mark.parametrize(
    "changes",
    [
        {"agentic_app_id": None},
        {"agentic_token_scope": None},
        {"agentic_token_scope": ""},
    ],
)
def test_incomplete_options_rejected_by_app(changes):
    socket_options = replace(options(), **changes)
    with pytest.raises(ValueError, match="agentic"):
        App(client_id=BLUEPRINT, client_secret="fake", tenant_id=TENANT, socket_mode=socket_options)


@pytest.mark.parametrize("partial_options", [{"agentic_tenant_id": TENANT}, {"agentic_token_scope": SCOPE}])
def test_partial_agentic_options_do_not_enable_classic_fallback(partial_options):
    socket_options = SocketModeOptions(**partial_options)
    with pytest.raises(ValueError, match="agentic_app_id"):
        App(socket_mode=socket_options)


@pytest.mark.parametrize(
    "credentials",
    [
        {"client_id": BLUEPRINT, "managed_identity_client_id": BLUEPRINT},
        {"client_id": BLUEPRINT, "managed_identity_client_id": "system"},
        {"client_id": BLUEPRINT, "token": lambda scope, tenant: None},
    ],
)
async def test_unsupported_credentials_rejected_by_token_provider(credentials):
    app = App(**credentials, tenant_id=TENANT, socket_mode=options())
    with pytest.raises(ValueError, match="agentic|Agentic"):
        await app.socket_mode._acquire_bot_token()
    await app.stop()


async def test_missing_tenant_rejected_by_token_provider(monkeypatch):
    monkeypatch.delenv("TENANT_ID", raising=False)
    app = App(client_id=BLUEPRINT, client_secret="fake", socket_mode=options())
    with pytest.raises(ValueError, match="tenant"):
        await app.socket_mode._acquire_bot_token()
    await app.stop()


async def test_missing_credentials_rejected_without_environment(monkeypatch):
    for key in ("CLIENT_ID", "CLIENT_SECRET", "TENANT_ID"):
        monkeypatch.delenv(key, raising=False)
    app = App(socket_mode=options())
    with pytest.raises(RuntimeError, match="agent-instance"):
        await app.socket_mode._acquire_bot_token()
    await app.stop()


async def test_empty_instance_rejected_by_token_provider_without_classic_fallback(monkeypatch):
    app = App(
        client_id=BLUEPRINT,
        client_secret="fake",
        tenant_id=TENANT,
        socket_mode=replace(options(), agentic_app_id=""),
    )
    classic = AsyncMock(side_effect=AssertionError("Must not use classic authentication"))
    monkeypatch.setattr(app.token_provider, "get_app_token", classic)
    with pytest.raises(ValueError, match="agentic_app_id"):
        await app.socket_mode._acquire_bot_token()
    classic.assert_not_awaited()
    await app.stop()


async def test_standalone_adapter_uses_supplied_token_callback():
    get_token = AsyncMock(side_effect=["first-instance-token", "fresh-instance-token"])
    adapter = SocketModeAdapter(options(), process_activity=AsyncMock(), get_app_token=get_token, client_id=BLUEPRINT)
    assert await adapter._acquire_bot_token() == "first-instance-token"
    assert await adapter._acquire_bot_token() == "fresh-instance-token"
    assert get_token.await_count == 2
    await adapter.stop()


async def test_socket_passes_scope_and_instance_to_token_provider(app_state):
    app, _, classic, agent, _ = app_state
    assert await app.socket_mode._acquire_bot_token() == "instance-token-1"
    agent.assert_awaited_once_with(SCOPE, "connection-instance", None)
    classic.assert_not_awaited()


async def test_socket_authentication_does_not_replace_global_app_token(app_state):
    app, _, classic, agent, _ = app_state
    classic.side_effect = None
    classic.return_value = "ordinary-app-token"
    assert await app._get_bot_token() == "ordinary-app-token"
    classic.assert_awaited_once_with()
    agent.assert_not_awaited()


@pytest.mark.parametrize(
    ("app_tenant", "socket_tenant", "expected_tenant"),
    [
        (TENANT, None, TENANT),
        (TENANT, "override-tenant", "override-tenant"),
        (None, "override-tenant", "override-tenant"),
    ],
)
async def test_named_provider_resolves_app_tenant_and_socket_override(
    monkeypatch, app_tenant, socket_tenant, expected_tenant
):
    monkeypatch.delenv("TENANT_ID", raising=False)

    class Provider:
        async def get_app_token(self, scope, tenant_id):
            raise AssertionError("Must not use classic authentication")

        async def get_agentic_app_token(self, scope, app_id, tenant_id):
            assert (scope, app_id, tenant_id) == (SCOPE, "connection-instance", expected_tenant)
            return None

    app = App(
        client_id=BLUEPRINT,
        tenant_id=app_tenant,
        token=Provider(),
        socket_mode=options(agentic_tenant_id=socket_tenant),
    )
    with pytest.raises(RuntimeError, match="agent-instance"):
        await app.socket_mode._acquire_bot_token()
    await app.stop()


@pytest.mark.parametrize("value", [None, "", " "])
async def test_empty_agentic_token_never_falls_back(app_state, value):
    app, _, classic, agent, _ = app_state
    agent.side_effect = None
    agent.return_value = value
    with pytest.raises(RuntimeError, match="agent-instance"):
        await app.socket_mode._acquire_bot_token()
    classic.assert_not_awaited()


async def test_agentic_token_failure_never_falls_back(app_state):
    app, _, classic, agent, _ = app_state
    agent.side_effect = ValueError("consent required")
    with pytest.raises(ValueError, match="consent required"):
        await app.socket_mode._acquire_bot_token()
    classic.assert_not_awaited()


@pytest.mark.parametrize(
    "field",
    [
        "agenticAppBlueprintId",
        "agenticAppId",
        "agenticUserId",
        "tenantId",
    ],
)
@pytest.mark.parametrize("value", [None, "", " ", " value ", 1])
async def test_incomplete_recipient_rejected_before_pipeline(app_state, monkeypatch, caplog, field, value):
    app, requests, classic, agent, user = app_state
    pipeline = AsyncMock()
    monkeypatch.setattr(app.socket_mode, "_process_activity", pipeline)
    env = envelope()
    env.payload["recipient"][field] = value
    result = await app.socket_mode._handle_envelope(env)
    assert result.status == 400
    assert result.bot_key == BLUEPRINT
    assert field in caplog.text
    pipeline.assert_not_awaited()
    classic.assert_not_awaited()
    agent.assert_not_awaited()
    user.assert_not_awaited()
    assert not requests


async def test_missing_all_recipient_metadata_rejected_in_agentic_mode(app_state, caplog):
    app, *_ = app_state
    env = envelope()
    env.payload["recipient"] = {"id": "au"}
    result = await app.socket_mode._handle_envelope(env)
    assert result.status == 400
    assert "agenticAppBlueprintId" in caplog.text


@pytest.mark.parametrize("value", [None, [], "recipient"])
async def test_invalid_recipient_shape_rejected_before_handler(app_state, monkeypatch, value):
    app, *_ = app_state
    pipeline = AsyncMock()
    monkeypatch.setattr(app.socket_mode, "_process_activity", pipeline)
    errors = []
    app.event("error")(errors.append)
    env = envelope()
    env.payload["recipient"] = value
    result = await app.socket_mode._handle_envelope(env)
    assert result.status == 400
    pipeline.assert_not_awaited()
    assert len(errors) == 1
    assert "recipient identity" in str(errors[0].error)


@pytest.mark.parametrize("case", ["ack", "invoke", "failure", "protocol"])
@pytest.mark.parametrize("key", [None, BLUEPRINT, "another-blueprint"])
async def test_reply_keys_and_mismatches(app_state, monkeypatch, case, key):
    app, *_ = app_state
    pipeline = AsyncMock(return_value=InvokeResponse(status=200, body={"ok": True}))
    if case == "failure":
        pipeline.side_effect = RuntimeError("handler error")
    monkeypatch.setattr(app.socket_mode, "_process_activity", pipeline)
    env = envelope(botKey=key, protocolVersion=999 if case == "protocol" else 1)
    if case != "ack":
        env.payload.update(type="invoke", name="task/fetch", value={})
    result = await app.socket_mode._handle_envelope(env)
    assert result.bot_key == BLUEPRINT
    if key == "another-blueprint":
        assert result.status == 400
        pipeline.assert_not_awaited()
    else:
        assert result.status == {"ack": 200, "invoke": 200, "failure": 500, "protocol": 400}[case]


async def test_recipient_blueprint_mismatch_rejected(app_state, monkeypatch):
    app, *_ = app_state
    pipeline = AsyncMock()
    monkeypatch.setattr(app.socket_mode, "_process_activity", pipeline)
    env = envelope()
    env.payload["recipient"]["agenticAppBlueprintId"] = "another-blueprint"
    result = await app.socket_mode._handle_envelope(env)
    assert result.status == 400
    pipeline.assert_not_awaited()


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"tenantId": TENANT},
        {"role": "agenticUser"},
        {"agenticAppBlueprintId": BLUEPRINT},
        {"agenticAppId": "instance"},
        {"agenticUserId": "user"},
    ],
)
async def test_classic_socket_leaves_recipient_handling_to_pipeline(metadata):
    pipeline = AsyncMock(return_value=InvokeResponse(status=200))
    adapter = SocketModeAdapter(process_activity=pipeline, get_app_token=AsyncMock(), client_id=BLUEPRINT)
    env = envelope()
    env.payload["recipient"] = {"id": "bot", **metadata}
    result = await adapter._handle_envelope(env)
    assert result.status == 200
    pipeline.assert_awaited_once()
    assert pipeline.await_args.args[0].body.model_dump()["recipient"] == env.payload["recipient"]


async def test_app_backed_recipient_uses_its_own_instance(app_state):
    app, requests, classic, agent, user = app_state

    @app.on_message
    async def reply(ctx):
        await ctx.send("app backed")

    env = envelope()
    del env.payload["recipient"]["agenticUserId"]
    del env.payload["recipient"]["role"]
    result = await app.socket_mode._handle_envelope(env)
    assert result.status == 200
    agent.assert_awaited_once_with(app.cloud.agent_bot_scope, "instance-1", "tenant-1")
    assert requests[0][1] == "Bearer instance-token-1"
    classic.assert_not_awaited()
    user.assert_not_awaited()


@pytest.mark.parametrize("reason", ["drop", "expiry"])
async def test_two_aus_keep_identity_across_reconnect_and_refresh(app_state, monkeypatch, reason):
    app, requests, classic, agent, user = app_state
    sockets = []
    negotiations = []
    second_ready = asyncio.Event()
    entered = 0
    gate = asyncio.Event()
    tokens = []
    completions = asyncio.Queue()

    def negotiate(request):
        negotiations.append(request.headers["authorization"])
        return httpx.Response(
            200,
            json={
                "url": "wss://signalr.example/client",
                "accessToken": "fake-signalr-token",
                "expiresIn": 61 if reason == "expiry" and len(negotiations) == 1 else 3600,
            },
        )

    async def open_socket(_url):
        socket = MockWebSocket()

        async def send(message):
            await MockWebSocket.send(socket, message)
            for part in message.split("\x1e"):
                if part:
                    frame = json.loads(part)
                    if frame.get("type") == 3:
                        completions.put_nowait(frame)

        monkeypatch.setattr(socket, "send", send)
        socket.incoming.put_nowait(
            encode_hub_message({})
            + encode_hub_message(
                {
                    "type": 1,
                    "target": "SocketReady",
                    "arguments": [{"botKey": BLUEPRINT}],
                }
            )
        )
        sockets.append(socket)
        return socket

    @app.on_message
    async def reply(ctx):
        nonlocal entered
        entered += 1
        if entered % 2 == 0:
            gate.set()
        await asyncio.wait_for(gate.wait(), 2)
        await ctx.send("identity check")

    def activity_event(event: ActivityEvent):
        tokens.append(event.token)

    app.event("activity")(activity_event)
    app.socket_mode.events.on("ready", lambda _: second_ready.set() if len(sockets) == 2 else None)
    transport = app.socket_mode._transport
    async with httpx.AsyncClient(transport=httpx.MockTransport(negotiate)) as client:
        monkeypatch.setattr(client, "send", HTTPX_SEND.__get__(client))
        monkeypatch.setattr(transport, "_http_client", client)
        monkeypatch.setattr(transport, "_websocket_factory", open_socket)
        try:
            await transport.start()
            for generation in (0, 1):
                gate.clear()
                socket = sockets[generation]
                for suffix in ("1", "2"):
                    env = envelope(suffix).model_dump(by_alias=True, exclude_none=True)
                    env["envelopeId"] = f"{generation}-{suffix}"
                    socket.incoming.put_nowait(
                        encode_hub_message(
                            {
                                "type": 1,
                                "target": "Activity",
                                "invocationId": env["envelopeId"],
                                "arguments": [env],
                            }
                        )
                    )
                replies = [await asyncio.wait_for(completions.get(), 3) for _ in range(2)]
                assert {reply["invocationId"] for reply in replies} == {f"{generation}-1", f"{generation}-2"}
                assert len(requests) == 2 * (generation + 1)
                if generation == 0:
                    if reason == "drop":
                        socket.incoming.put_nowait(ConnectionError("network drop"))
                    await asyncio.wait_for(second_ready.wait(), 3)
            assert negotiations == ["Bearer instance-token-1", "Bearer instance-token-2"]
            assert agent.await_count == 2
            assert all(call.args == (SCOPE, "connection-instance", None) for call in agent.await_args_list)
            assert user.await_count == 4
            classic.assert_not_awaited()
            for url, authorization, body in requests:
                suffix = body["from"]["agenticUserId"][-1]
                assert body["from"] == recipient(suffix)
                assert authorization == f"Bearer tenant-{suffix}:instance-{suffix}:user-{suffix}"
                assert url == f"{SERVICE}/v3/conversations/conversation-{suffix}/activities"
            assert len(tokens) == 4
            assert all(
                token.app_id == BLUEPRINT and str(token) == "" and token.service_url == SERVICE for token in tokens
            )
            for socket in sockets:
                frames = [json.loads(part) for message in socket.sent for part in message.split("\x1e") if part]
                replies = [frame["result"] for frame in frames if frame.get("type") == 3]
                assert len(replies) == 2
                assert all(reply["status"] == 200 and reply["botKey"] == BLUEPRINT for reply in replies)
        finally:
            await transport.stop()
    assert transport.status == "stopped"
    assert all(socket.closed for socket in sockets)
