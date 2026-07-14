"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import cast

import httpx
import pytest
from microsoft_teams.api.auth.cloud_environment import US_GOV
from microsoft_teams.api.clients import ApiClient
from microsoft_teams.api.clients._auth_provider_interceptor import AuthProviderInterceptor
from microsoft_teams.api.clients.base_client import BaseClient
from microsoft_teams.api.models import AgenticIdentity
from microsoft_teams.common import Client, ClientOptions, Interceptor, Token


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


def use_auth_provider(
    http_client: Client,
    auth_provider: RecordingAuthProvider,
    default_agentic_identity: AgenticIdentity | None = None,
) -> None:
    http_client.use_interceptor(
        cast(Interceptor, AuthProviderInterceptor(auth_provider, default_agentic_identity=default_agentic_identity))
    )


def test_api_client_adds_auth_provider_interceptor_once_for_shared_http_client():
    http_client, _ = create_client()
    auth_provider = RecordingAuthProvider()

    ApiClient("https://test.service.url", http_client, auth_provider=auth_provider)
    ApiClient("https://test.service.url", http_client, auth_provider=auth_provider)

    assert len(http_client.http.event_hooks["request"]) == 1


def test_api_client_uses_cloud_token_service_url_for_default_settings():
    client = ApiClient("https://test.service.url", cloud=US_GOV)

    assert client._api_client_settings.oauth_url == US_GOV.token_service_url


@pytest.mark.asyncio
async def test_explicit_request_token_wins_over_auth_provider_and_http_client_token():
    http_client, recorder = create_client(default_token="http-client-token")
    auth_provider = RecordingAuthProvider()
    use_auth_provider(http_client, auth_provider)
    client = HarnessClient(http_client)

    await client.post_resource(token="explicit-token")

    assert auth_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer explicit-token"


@pytest.mark.asyncio
async def test_explicit_authorization_header_wins_over_auth_provider():
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider()
    use_auth_provider(http_client, auth_provider)
    client = HarnessClient(http_client)

    await client.post_resource(headers={"Authorization": "Bearer explicit-header-token"})

    assert auth_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer explicit-header-token"


@pytest.mark.asyncio
async def test_http_client_token_wins_over_auth_provider_token():
    http_client, recorder = create_client(default_token="http-client-token")
    auth_provider = RecordingAuthProvider()
    use_auth_provider(http_client, auth_provider)
    client = HarnessClient(http_client)

    await client.post_resource()

    assert auth_provider.calls == []
    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"


@pytest.mark.asyncio
async def test_auth_provider_token_is_used_when_request_has_no_auth():
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider()
    use_auth_provider(http_client, auth_provider)
    client = HarnessClient(http_client)

    await client.post_resource()

    assert auth_provider.calls == [(None, None)]
    assert recorder.last_request.headers["authorization"] == "Bearer auth-provider-token"


@pytest.mark.asyncio
async def test_no_authorization_is_added_when_auth_provider_returns_none():
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider(token_value=None)
    use_auth_provider(http_client, auth_provider)
    client = HarnessClient(http_client)

    await client.post_resource()

    assert auth_provider.calls == [(None, None)]
    assert "authorization" not in recorder.last_request.headers


@pytest.mark.asyncio
async def test_no_authorization_is_added_when_auth_provider_returns_blank_token(caplog):
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider(token_value="   ")
    use_auth_provider(http_client, auth_provider)
    client = HarnessClient(http_client)

    with caplog.at_level(logging.WARNING):
        await client.post_resource()

    assert auth_provider.calls == [(None, None)]
    assert "authorization" not in recorder.last_request.headers
    assert "Auth provider returned an empty token" in caplog.text


@pytest.mark.asyncio
async def test_http_client_token_is_used_when_no_auth_provider():
    http_client, recorder = create_client(default_token="http-client-token")
    client = HarnessClient(http_client)

    await client.post_resource()

    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"


@pytest.mark.asyncio
async def test_default_agentic_identity_is_used_without_request_metadata():
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider(token_value="agentic-token")
    identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
    use_auth_provider(http_client, auth_provider, default_agentic_identity=identity)
    client = HarnessClient(http_client)

    await client.post_resource()

    assert auth_provider.calls == [(None, identity)]
    assert recorder.last_request.headers["authorization"] == "Bearer agentic-token"


@pytest.mark.asyncio
async def test_default_agentic_identity_is_passed_to_auth_provider_interceptor():
    http_client, recorder = create_client()
    auth_provider = RecordingAuthProvider(token_value="agentic-token")
    identity = AgenticIdentity("agentic-app-id", "agentic-user-id", tenant_id="tenant-id")
    use_auth_provider(http_client, auth_provider, default_agentic_identity=identity)
    client = HarnessClient(http_client)

    await client.post_resource()

    assert auth_provider.calls == [(None, identity)]
    assert recorder.last_request.headers["authorization"] == "Bearer agentic-token"


@pytest.mark.asyncio
async def test_http_client_token_still_wins_without_auth_provider():
    http_client, recorder = create_client(default_token="http-client-token")
    client = HarnessClient(http_client)

    await client.post_resource()

    assert recorder.last_request.headers["authorization"] == "Bearer http-client-token"
