"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from contextlib import contextmanager
from typing import Any, Iterator
from unittest.mock import patch

import httpx
import pytest
from microsoft_teams.api.auth.cloud_environment import PUBLIC, US_GOV
from microsoft_teams.api.clients import ApiClient
from microsoft_teams.api.clients.base_client import BaseClient
from microsoft_teams.api.diagnostics._outbound import ApiOutboundTelemetryMiddleware
from microsoft_teams.api.models import AgenticIdentity
from microsoft_teams.common import Client, ClientOptions, Token
from opentelemetry.trace import SpanKind


class RecordingSpan:
    def __init__(self, name: str, options: dict[str, Any]):
        self.name = name
        self.options = options
        self.attributes: dict[str, str] = {}

    def set_attribute(self, key: str, value: str) -> None:
        self.attributes[key] = value


class RecordingTracer:
    def __init__(self):
        self.spans: list[RecordingSpan] = []

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs: Any) -> Iterator[RecordingSpan]:
        span = RecordingSpan(name, kwargs)
        self.spans.append(span)
        yield span


class RequestRecorder:
    def __init__(self):
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, json={"ok": True}, headers={"content-type": "application/json"})

    @property
    def last_request(self) -> httpx.Request:
        return self.requests[-1]


class RecordingTokenProvider:
    def __init__(self, token_value: str | None = "auth-provider-token"):
        self._token_value = token_value
        self.calls: list[tuple[str, str, str | None, str | None, str | None]] = []

    def get_app_token(self, scope: str, tenant_id: str | None) -> str | None:
        self.calls.append(("app", scope, None, None, tenant_id))
        return self._token_value

    def get_agentic_user_token(
        self,
        scope: str,
        agentic_app_id: str,
        agentic_user_id: str,
        tenant_id: str | None,
    ) -> str | None:
        self.calls.append(("agentic_user", scope, agentic_app_id, agentic_user_id, tenant_id))
        return self._token_value

    def get_agentic_app_token(self, scope: str, agentic_app_id: str, tenant_id: str | None) -> str | None:
        self.calls.append(("agentic_app", scope, agentic_app_id, None, tenant_id))
        return self._token_value


class RaisingTokenProvider(RecordingTokenProvider):
    def __init__(self):
        super().__init__()
        self.exception = RuntimeError("token failure")

    def get_app_token(self, scope: str, tenant_id: str | None):
        self.calls.append(("app", scope, None, None, tenant_id))
        raise self.exception


class HarnessClient(BaseClient):
    async def post_resource(
        self,
        *,
        token: Token | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        return await self.http.post(
            "/resource",
            json={"ok": True},
            headers=headers,
            token=token,
        )


def create_client(*, default_token: Token | None = None) -> tuple[Client, RequestRecorder]:
    recorder = RequestRecorder()
    client = Client(ClientOptions(base_url="https://mock.api.com", token=default_token))
    client.http._transport = httpx.MockTransport(recorder.handler)
    return client, recorder


def create_token_provider_harness(
    token_provider: RecordingTokenProvider,
    default_agentic_identity: AgenticIdentity | None = None,
) -> tuple[HarnessClient, RequestRecorder]:
    http_client, recorder = create_client()
    api_client = ApiClient(
        "https://test.service.url",
        http_client,
        token_provider=token_provider,
        agentic_identity=default_agentic_identity,
    )
    return HarnessClient(api_client.http), recorder


def test_api_client_uses_http_token_for_token_provider_without_mutating_source_client():
    http_client, _ = create_client()
    token_provider = RecordingTokenProvider()

    api_client = ApiClient("https://test.service.url", http_client, token_provider=token_provider)

    assert http_client.token is None
    assert api_client.http.token is not None
    assert api_client.http.http is http_client.http
    assert api_client.http.interceptors == http_client.interceptors


def test_api_client_registers_outbound_telemetry_middleware_once_across_clones():
    api_client = ApiClient("https://test.service.url")

    scoped = api_client.from_service_url("https://override.service.url")

    assert (
        sum(isinstance(middleware, ApiOutboundTelemetryMiddleware) for middleware in api_client.http.middlewares) == 1
    )
    assert sum(isinstance(middleware, ApiOutboundTelemetryMiddleware) for middleware in scoped.http.middlewares) == 1


def test_api_client_uses_cloud_token_service_url_for_default_settings():
    client = ApiClient("https://test.service.url", cloud=US_GOV)

    assert client._api_client_settings.oauth_url == US_GOV.token_service_url


@pytest.mark.asyncio
async def test_explicit_request_token_wins_over_token_provider_and_http_client_token():
    http_client, recorder = create_client()
    token_provider = RecordingTokenProvider()
    api_client = ApiClient("https://test.service.url", http_client, token_provider=token_provider)
    client = HarnessClient(api_client.http)

    await client.post_resource(token="explicit-token")

    assert token_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer explicit-token"


@pytest.mark.asyncio
async def test_explicit_authorization_header_wins_over_token_provider():
    token_provider = RecordingTokenProvider()
    client, recorder = create_token_provider_harness(token_provider)

    await client.post_resource(headers={"Authorization": "Bearer explicit-header-token"})

    assert token_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer explicit-header-token"


def test_http_client_token_conflicts_with_token_provider():
    token_provider = RecordingTokenProvider()
    http_client, _ = create_client(default_token="http-client-token")

    with pytest.raises(ValueError, match="token provider and an HTTP client token"):
        ApiClient("https://test.service.url", http_client, token_provider=token_provider)


@pytest.mark.asyncio
async def test_token_provider_token_is_used_when_request_has_no_auth():
    token_provider = RecordingTokenProvider()
    client, recorder = create_token_provider_harness(token_provider)

    await client.post_resource()

    assert token_provider.calls == [("app", PUBLIC.bot_scope, None, None, None)]
    assert recorder.last_request.headers["authorization"] == "Bearer auth-provider-token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agentic_identity", "expected_flow"),
    [
        (None, "app_only"),
        (
            AgenticIdentity(
                agentic_app_blueprint_id="blueprint-id",
                agentic_app_id="agentic-app-id",
                agentic_user_id="agentic-user-id",
                tenant_id="tenant-id",
            ),
            "agentic_user",
        ),
        (
            AgenticIdentity(
                agentic_app_blueprint_id="blueprint-id",
                agentic_app_id="agentic-app-id",
                tenant_id="tenant-id",
            ),
            "agentic_app",
        ),
    ],
)
async def test_token_provider_token_records_auth_outbound_span(agentic_identity, expected_flow):
    token_provider = RecordingTokenProvider()
    client, recorder = create_token_provider_harness(token_provider, default_agentic_identity=agentic_identity)
    tracer = RecordingTracer()

    with patch("microsoft_teams.api.clients.api_client.get_tracer", return_value=tracer):
        await client.post_resource()

    assert "authorization" in recorder.last_request.headers
    assert len(tracer.spans) == 1
    span = tracer.spans[0]
    assert span.name == "microsoft.teams.auth.outbound"
    assert span.options == {
        "kind": SpanKind.CLIENT,
        "record_exception": False,
        "set_status_on_exception": False,
    }
    assert span.attributes == {"auth.flow": expected_flow}


@pytest.mark.asyncio
async def test_token_provider_token_records_exception_before_reraising():
    token_provider = RaisingTokenProvider()
    client, _ = create_token_provider_harness(token_provider)
    tracer = RecordingTracer()

    with (
        patch("microsoft_teams.api.clients.api_client.get_tracer", return_value=tracer),
        patch("microsoft_teams.api.clients.api_client.record_exception") as record_exception,
        pytest.raises(RuntimeError, match="token failure"),
    ):
        await client.post_resource()

    assert token_provider.calls == [("app", PUBLIC.bot_scope, None, None, None)]
    assert tracer.spans[0].attributes == {"auth.flow": "app_only"}
    record_exception.assert_called_once_with(tracer.spans[0], token_provider.exception)


@pytest.mark.asyncio
async def test_no_authorization_is_added_when_token_provider_returns_none():
    token_provider = RecordingTokenProvider(token_value=None)
    client, recorder = create_token_provider_harness(token_provider)

    await client.post_resource()

    assert token_provider.calls == [("app", PUBLIC.bot_scope, None, None, None)]
    assert "authorization" not in recorder.last_request.headers


@pytest.mark.asyncio
async def test_http_client_token_is_used_when_no_token_provider():
    http_client, recorder = create_client(default_token="http-client-token")
    client = HarnessClient(http_client)

    await client.post_resource()

    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"


@pytest.mark.asyncio
async def test_default_agentic_identity_is_used_without_request_metadata():
    token_provider = RecordingTokenProvider(token_value="agentic-user-token")
    identity = AgenticIdentity(
        agentic_app_blueprint_id="blueprint-id",
        agentic_app_id="agentic-app-id",
        agentic_user_id="agentic-user-id",
        tenant_id="tenant-id",
    )
    client, recorder = create_token_provider_harness(token_provider, default_agentic_identity=identity)

    await client.post_resource()

    assert token_provider.calls == [
        ("agentic_user", PUBLIC.agent_bot_scope, "agentic-app-id", "agentic-user-id", "tenant-id")
    ]
    assert recorder.last_request.headers["authorization"] == "Bearer agentic-user-token"


@pytest.mark.asyncio
async def test_default_agentic_identity_is_passed_to_token_provider():
    token_provider = RecordingTokenProvider(token_value="agentic-user-token")
    identity = AgenticIdentity(
        agentic_app_blueprint_id="blueprint-id",
        agentic_app_id="agentic-app-id",
        agentic_user_id="agentic-user-id",
        tenant_id="tenant-id",
    )
    client, recorder = create_token_provider_harness(token_provider, default_agentic_identity=identity)

    await client.post_resource()

    assert token_provider.calls == [
        ("agentic_user", PUBLIC.agent_bot_scope, "agentic-app-id", "agentic-user-id", "tenant-id")
    ]
    assert recorder.last_request.headers["authorization"] == "Bearer agentic-user-token"


@pytest.mark.asyncio
async def test_user_backed_agentic_identity_requires_user_token_provider_capability():
    calls = []

    class AppOnlyTokenProvider:
        def get_app_token(self, scope: str, tenant_id: str | None):
            calls.append((scope, tenant_id))
            return "app-token"

    http_client, _ = create_client()
    identity = AgenticIdentity(
        agentic_app_blueprint_id="blueprint-id",
        agentic_app_id="agentic-app-id",
        agentic_user_id="agentic-user-id",
        tenant_id="tenant-id",
    )
    api_client = ApiClient(
        "https://test.service.url",
        http_client,
        token_provider=AppOnlyTokenProvider(),
        agentic_identity=identity,
    )
    client = HarnessClient(api_client.http)

    with pytest.raises(ValueError, match="does not implement get_agentic_user_token"):
        await client.post_resource()

    assert calls == []


@pytest.mark.asyncio
async def test_app_backed_agentic_identity_requires_app_token_provider_capability():
    calls = []

    class AppOnlyTokenProvider:
        def get_app_token(self, scope: str, tenant_id: str | None):
            calls.append((scope, tenant_id))
            return "app-token"

    http_client, _ = create_client()
    identity = AgenticIdentity(
        agentic_app_blueprint_id="blueprint-id",
        agentic_app_id="agentic-app-id",
        tenant_id="tenant-id",
    )
    api_client = ApiClient(
        "https://test.service.url",
        http_client,
        token_provider=AppOnlyTokenProvider(),
        agentic_identity=identity,
    )
    client = HarnessClient(api_client.http)

    with pytest.raises(ValueError, match="does not implement get_agentic_app_token"):
        await client.post_resource()

    assert calls == []


@pytest.mark.asyncio
async def test_http_client_token_still_wins_without_token_provider():
    http_client, recorder = create_client(default_token="http-client-token")
    client = HarnessClient(http_client)

    await client.post_resource()

    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"
