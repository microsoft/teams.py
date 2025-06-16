"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import httpx
import pytest
from microsoft.teams.common.http.client import Client, ClientOptions
from microsoft.teams.common.http.client_token import StringLike


class DummyAsyncInterceptor:
    def __init__(self):
        self.request_called = False
        self.response_called = False

    async def request(self, ctx):
        self.request_called = True

    async def response(self, ctx):
        self.response_called = True


class DummySyncInterceptor:
    def __init__(self):
        self.request_called = False
        self.response_called = False

    def request(self, ctx):
        self.request_called = True

    def response(self, ctx):
        self.response_called = True


class CustomStringLike(StringLike):
    def __str__(self) -> str:
        return "custom-token"


async def async_token_factory() -> str:
    return "async-token"


def sync_token_factory() -> str:
    return "sync-token"


@pytest.fixture
def mock_transport():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "url": str(request.url), "headers": dict(request.headers.items())})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_request_merges_headers_and_token(mock_transport):
    interceptor = DummyAsyncInterceptor()
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            headers={"X-Default": "foo"},
            token="abc123",
            interceptors=[interceptor],
        )
    )
    client.http._transport = mock_transport

    resp = await client.get("/test", headers={"X-Custom": "bar"}, token="override")
    data = resp.json()
    assert data["ok"] is True
    assert data["url"].endswith("/test")
    assert interceptor.request_called


@pytest.mark.parametrize(
    "interceptor",
    [
        DummyAsyncInterceptor(),
        DummySyncInterceptor(),
    ],
)
@pytest.mark.asyncio
async def test_post_request_and_response_interceptor(mock_transport, interceptor):
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            interceptors=[interceptor],
        )
    )
    client.http._transport = mock_transport

    resp = await client.post("/post", data="payload")
    assert resp.status_code == 200
    assert interceptor.request_called
    assert interceptor.response_called


@pytest.mark.asyncio
async def test_clone_merges_options_and_interceptors(mock_transport):
    interceptor1 = DummyAsyncInterceptor()
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            headers={"X-Default": "foo"},
            interceptors=[interceptor1],
        )
    )
    client.http._transport = mock_transport

    interceptor2 = DummyAsyncInterceptor()
    clone = client.clone(ClientOptions(headers={"X-Clone": "bar"}, interceptors=[interceptor2]))
    clone.http._transport = mock_transport

    resp = await clone.get("/clone")
    assert resp.status_code == 200
    assert not interceptor1.request_called
    assert interceptor2.request_called


@pytest.mark.parametrize(
    "token,expected",
    [
        ("simple-token", "Bearer simple-token"),
        (CustomStringLike(), "Bearer custom-token"),
        (sync_token_factory, "Bearer sync-token"),
        (async_token_factory, "Bearer async-token"),
        (None, None),
        (lambda: None, None),
        (lambda: CustomStringLike(), "Bearer custom-token"),
        (lambda: "lambda-token", "Bearer lambda-token"),
    ],
)
@pytest.mark.asyncio
async def test_token_types(mock_transport, token, expected):
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            token=token,
        )
    )
    client.http._transport = mock_transport

    resp = await client.get("/token-test")
    data = resp.json()

    if expected is None:
        assert "authorization" not in data["headers"]
    else:
        assert data["headers"]["authorization"] == expected


# Test async token factory that returns None
async def async_none_factory() -> None:
    return None


@pytest.mark.asyncio
async def test_async_none_token(mock_transport):
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            token=async_none_factory,
        )
    )
    client.http._transport = mock_transport

    resp = await client.get("/token-test")
    data = resp.json()
    assert "authorization" not in data["headers"]


# Test token factory that raises an exception
def failing_token_factory() -> str:
    raise ValueError("Token factory failed")


@pytest.mark.asyncio
async def test_failing_token_factory(mock_transport):
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            token=failing_token_factory,
        )
    )
    client.http._transport = mock_transport

    with pytest.raises(ValueError, match="Token factory failed"):
        await client.get("/token-test")
