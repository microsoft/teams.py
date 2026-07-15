"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import httpx
import pytest
from microsoft_teams.common.http import Client, ClientOptions, Interceptor
from microsoft_teams.common.http.client_token import StringLike


class DummyAsyncInterceptor(Interceptor):
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

    resp = await client.post("/post", data={"payload": "test_data"})
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


def test_interceptors_returns_read_only_copy():
    interceptor1 = DummyAsyncInterceptor()
    client = Client(ClientOptions(interceptors=[interceptor1]))

    assert client.interceptors == (interceptor1,)


def test_clone_copies_interceptor_list_independently():
    interceptor1 = DummyAsyncInterceptor()
    client = Client(ClientOptions(interceptors=[interceptor1]))

    clone = client.clone()
    interceptor2 = DummyAsyncInterceptor()
    clone.use_interceptor(interceptor2)

    assert client.interceptors == (interceptor1,)
    assert clone.interceptors == (interceptor1, interceptor2)
    assert client.interceptors is not clone.interceptors


def test_clone_reuses_underlying_http_client_when_requested():
    client = Client(ClientOptions(base_url="https://example.com"))

    clone = client.clone(share_http=True)

    assert clone is not client
    assert clone.http is client.http


def test_clone_can_clear_interceptors_with_empty_override():
    interceptor1 = DummyAsyncInterceptor()
    client = Client(ClientOptions(interceptors=[interceptor1]))

    clone = client.clone(ClientOptions(interceptors=[]))

    assert client.interceptors == (interceptor1,)
    assert clone.interceptors == ()


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


@pytest.mark.asyncio
async def test_explicit_authorization_header_wins_over_default_token(mock_transport):
    client = Client(ClientOptions(base_url="https://example.com", token="default-token"))
    client.http._transport = mock_transport

    resp = await client.get("/token-test", headers={"Authorization": "******"})
    data = resp.json()

    assert data["headers"]["authorization"] == "******"


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


def test_clone_preserves_user_agent_without_overrides():
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0"}))
    clone = client.clone()
    assert clone._options.headers["User-Agent"] == "teams-bot/1.0"


def test_clone_merges_user_agent_with_override():
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0"}))
    clone = client.clone(ClientOptions(headers={"User-Agent": "myapp/2.0"}))
    assert clone._options.headers["User-Agent"] == "teams-bot/1.0 myapp/2.0"


def test_clone_with_other_headers_preserves_original_user_agent():
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0"}))
    clone = client.clone(ClientOptions(headers={"X-Custom": "value"}))
    assert clone._options.headers["User-Agent"] == "teams-bot/1.0"
    assert clone._options.headers["X-Custom"] == "value"


def test_clone_user_agent_case_insensitive():
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0"}))
    clone = client.clone(ClientOptions(headers={"user-agent": "myapp/2.0"}))
    ua = clone._options.headers["User-Agent"]
    assert "teams-bot/1.0" in ua
    assert "myapp/2.0" in ua


def test_clone_user_agent_no_duplicate_token():
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0 myapp/2.0"}))
    clone = client.clone(ClientOptions(headers={"User-Agent": "myapp/2.0"}))
    ua = clone._options.headers["User-Agent"]
    assert ua.count("myapp/2.0") == 1


def test_clone_user_agent_no_false_positive_substring():
    # "bot" is a substring of "teams-bot/1.0" but should still be appended as a distinct token
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0"}))
    clone = client.clone(ClientOptions(headers={"User-Agent": "bot"}))
    ua = clone._options.headers["User-Agent"]
    assert ua == "teams-bot/1.0 bot"


def test_clone_only_override_user_agent_kept_when_base_has_none():
    client = Client(ClientOptions(headers={}))
    clone = client.clone(ClientOptions(headers={"User-Agent": "myapp/2.0"}))
    assert clone._options.headers["User-Agent"] == "myapp/2.0"


def test_clone_normalizes_user_agent_key_when_base_has_none():
    client = Client(ClientOptions(headers={}))
    clone = client.clone(ClientOptions(headers={"user-agent": "myapp/2.0"}))
    assert "User-Agent" in clone._options.headers
    assert clone._options.headers["User-Agent"] == "myapp/2.0"


def test_clone_user_agent_multi_token_override():
    client = Client(ClientOptions(headers={"User-Agent": "teams-bot/1.0"}))
    clone = client.clone(ClientOptions(headers={"User-Agent": "myapp/2.0 partner/3.0"}))
    ua = clone._options.headers["User-Agent"]
    assert ua == "teams-bot/1.0 myapp/2.0 partner/3.0"
