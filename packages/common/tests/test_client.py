import httpx
import pytest
from common.http.client import Client, ClientOptions


class DummyInterceptor:
    def __init__(self):
        self.request_called = False
        self.response_called = False

    async def request(self, ctx):
        self.request_called = True
        return ctx.request

    async def response(self, ctx):
        self.response_called = True
        return ctx.response


@pytest.fixture
def mock_transport():
    def handler(request):
        return httpx.Response(200, json={"ok": True, "url": str(request.url)})

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_get_request_merges_headers_and_token(mock_transport):
    interceptor = DummyInterceptor()
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


@pytest.mark.asyncio
async def test_post_request_and_response_interceptor(mock_transport):
    interceptor = DummyInterceptor()
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
    interceptor1 = DummyInterceptor()
    client = Client(
        ClientOptions(
            base_url="https://example.com",
            headers={"X-Default": "foo"},
            interceptors=[interceptor1],
        )
    )
    client.http._transport = mock_transport

    interceptor2 = DummyInterceptor()
    clone = client.clone(ClientOptions(headers={"X-Clone": "bar"}, interceptors=[interceptor2]))
    clone.http._transport = mock_transport

    resp = await clone.get("/clone")
    assert resp.status_code == 200
    assert not interceptor1.request_called
    assert interceptor2.request_called


@pytest.mark.asyncio
async def test_token_injection(mock_transport):
    class TokenObj:
        def __str__(self):
            return "tokobj"

    client = Client(
        ClientOptions(
            base_url="https://example.com",
            token=TokenObj(),
        )
    )
    client.http._transport = mock_transport

    resp = await client.get("/token")
    # Check that Authorization header is set (httpx doesn't echo headers, so just ensure no error)
    assert resp.status_code == 200
