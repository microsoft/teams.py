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
from microsoft_teams.api.auth.cloud_environment import US_GOV
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


class RecordingAuthProvider:
    def __init__(self, token_value: str | None = "auth-provider-token"):
        self._token_value = token_value
        self.calls: list[tuple[str | None, AgenticIdentity | None]] = []

    def token(
        self,
        *,
        scope: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ) -> str | None:
        self.calls.append((scope, agentic_identity))
        return self._token_value


class RaisingAuthProvider(RecordingAuthProvider):
    def __init__(self):
        super().__init__()
        self.exception = RuntimeError("token failure")

    def token(
        self,
        *,
        scope: str | None = None,
        agentic_identity: AgenticIdentity | None = None,
    ):
        self.calls.append((scope, agentic_identity))
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


def create_auth_provider_harness(
    auth_provider: RecordingAuthProvider,
    default_agentic_identity: AgenticIdentity | None = None,
) -> tuple[HarnessClient, RequestRecorder]:
    http_client, recorder = create_client()
    api_client = ApiClient(
        "https://test.service.url",
        http_client,
        auth_provider=auth_provider,
        agentic_identity=default_agentic_identity,
    )
    return HarnessClient(api_client.http), recorder


def test_api_client_uses_http_token_for_auth_provider_without_mutating_source_client():
    http_client, _ = create_client()
    auth_provider = RecordingAuthProvider()

    api_client = ApiClient("https://test.service.url", http_client, auth_provider=auth_provider)

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
async def test_explicit_request_token_wins_over_auth_provider_and_http_client_token():
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider()
    api_client = ApiClient("https://test.service.url", http_client, auth_provider=auth_provider)
    client = HarnessClient(api_client.http)

    await client.post_resource(token="explicit-token")

    assert auth_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer explicit-token"


@pytest.mark.asyncio
async def test_explicit_authorization_header_wins_over_auth_provider():
    auth_provider = RecordingAuthProvider()
    client, recorder = create_auth_provider_harness(auth_provider)

    await client.post_resource(headers={"Authorization": "Bearer explicit-header-token"})

    assert auth_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer explicit-header-token"


def test_http_client_token_conflicts_with_auth_provider():
    auth_provider = RecordingAuthProvider()
    http_client, _ = create_client(default_token="http-client-token")

    with pytest.raises(ValueError, match="auth provider and an HTTP client token"):
        ApiClient("https://test.service.url", http_client, auth_provider=auth_provider)


@pytest.mark.asyncio
async def test_auth_provider_token_is_used_when_request_has_no_auth():
    auth_provider = RecordingAuthProvider()
    client, recorder = create_auth_provider_harness(auth_provider)

    await client.post_resource()

    assert auth_provider.calls == [(None, None)]
    assert recorder.last_request.headers["authorization"] == "Bearer auth-provider-token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("agentic_identity", "expected_flow"),
    [
        (None, "app_only"),
        (AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id"), "agentic"),
    ],
)
async def test_auth_provider_token_records_auth_outbound_span(agentic_identity, expected_flow):
    auth_provider = RecordingAuthProvider()
    client, recorder = create_auth_provider_harness(auth_provider, default_agentic_identity=agentic_identity)
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
async def test_auth_provider_token_records_exception_before_reraising():
    auth_provider = RaisingAuthProvider()
    client, _ = create_auth_provider_harness(auth_provider)
    tracer = RecordingTracer()

    with (
        patch("microsoft_teams.api.clients.api_client.get_tracer", return_value=tracer),
        patch("microsoft_teams.api.clients.api_client.record_exception") as record_exception,
        pytest.raises(RuntimeError, match="token failure"),
    ):
        await client.post_resource()

    assert auth_provider.calls == [(None, None)]
    assert tracer.spans[0].attributes == {"auth.flow": "app_only"}
    record_exception.assert_called_once_with(tracer.spans[0], auth_provider.exception)


@pytest.mark.asyncio
async def test_no_authorization_is_added_when_auth_provider_returns_none():
    auth_provider = RecordingAuthProvider(token_value=None)
    client, recorder = create_auth_provider_harness(auth_provider)

    await client.post_resource()

    assert auth_provider.calls == [(None, None)]
    assert "authorization" not in recorder.last_request.headers


@pytest.mark.asyncio
async def test_http_client_token_is_used_when_no_auth_provider():
    http_client, recorder = create_client(default_token="http-client-token")
    client = HarnessClient(http_client)

    await client.post_resource()

    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"


@pytest.mark.asyncio
async def test_default_agentic_identity_is_used_without_request_metadata():
    auth_provider = RecordingAuthProvider(token_value="agentic-token")
    identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
    client, recorder = create_auth_provider_harness(auth_provider, default_agentic_identity=identity)

    await client.post_resource()

    assert auth_provider.calls == [(None, identity)]
    assert recorder.last_request.headers["authorization"] == "Bearer agentic-token"


@pytest.mark.asyncio
async def test_default_agentic_identity_is_passed_to_auth_provider_token():
    auth_provider = RecordingAuthProvider(token_value="agentic-token")
    identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
    client, recorder = create_auth_provider_harness(auth_provider, default_agentic_identity=identity)

    await client.post_resource()

    assert auth_provider.calls == [(None, identity)]
    assert recorder.last_request.headers["authorization"] == "Bearer agentic-token"


@pytest.mark.asyncio
async def test_http_client_token_still_wins_without_auth_provider():
    http_client, recorder = create_client(default_token="http-client-token")
    client = HarnessClient(http_client)

    await client.post_resource()

    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"
