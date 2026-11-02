"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import httpx2
import pytest
from microsoft_teams.common.http import (
    Client,
    ClientOptions,
    Interceptor,
    InterceptorRequestContext,
    InterceptorResponseContext,
    MiddlewareContext,
    MiddlewareNext,
)
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


class RecordingMiddleware:
    def __init__(self, name: str, events: list[str]) -> None:
        self.name = name
        self.events = events

    async def send(self, context: MiddlewareContext, next: MiddlewareNext) -> httpx2.Response:
        self.events.append(f"{self.name}:before:{context.method}")
        response = await next()
        self.events.append(f"{self.name}:after:{response.status_code}")
        return response


class CustomStringLike(StringLike):
    def __str__(self) -> str:
        return "custom-token"


async def async_token_factory() -> str:
    return "async-token"


def sync_token_factory() -> str:
    return "sync-token"


def create_mock_client(transport: httpx2.MockTransport, options: ClientOptions | None = None) -> Client:
    options = options or ClientOptions(base_url="https://example.com")
    return Client(
        options,
        _http=httpx2.AsyncClient(
            transport=transport,
            base_url=options.base_url or "",
            headers=options.headers,
            timeout=options.timeout,
        ),
    )


@pytest.fixture
async def use_mock_transport(monkeypatch):
    raw_clients: list[httpx2.AsyncClient] = []
    async_client = httpx2.AsyncClient

    def install(transport: httpx2.MockTransport) -> None:
        def create(**kwargs) -> httpx2.AsyncClient:
            kwargs.pop("transport", None)
            raw = async_client(transport=transport, **kwargs)
            raw_clients.append(raw)
            return raw

        monkeypatch.setattr(httpx2, "AsyncClient", create)

    yield install
    for raw in raw_clients:
        await raw.aclose()


@pytest.fixture
def mock_transport(use_mock_transport):
    def handler(request):
        return httpx2.Response(
            200, json={"ok": True, "url": str(request.url), "headers": dict(request.headers.items())}
        )

    transport = httpx2.MockTransport(handler)
    use_mock_transport(transport)
    return transport


@pytest.mark.asyncio
@pytest.mark.parametrize("proxy", [None, "http://127.0.0.1:1"])
async def test_get_request_merges_headers_and_token(mock_transport, monkeypatch, proxy):
    if proxy is not None:
        monkeypatch.setenv("HTTPS_PROXY", proxy)
        monkeypatch.setenv("ALL_PROXY", proxy)
        monkeypatch.setenv("NO_PROXY", "")
    interceptor = DummyAsyncInterceptor()
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            headers={"X-Default": "foo"},
            token="abc123",
            interceptors=[interceptor],
        ),
    )
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
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            interceptors=[interceptor],
        ),
    )
    resp = await client.post("/post", data={"payload": "test_data"})
    assert resp.status_code == 200
    assert interceptor.request_called
    assert interceptor.response_called


@pytest.mark.asyncio
async def test_clone_merges_options_and_interceptors(mock_transport):
    interceptor1 = DummyAsyncInterceptor()
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            headers={"X-Default": "foo"},
            interceptors=[interceptor1],
        ),
    )
    interceptor2 = DummyAsyncInterceptor()
    clone = client.clone(ClientOptions(headers={"X-Clone": "bar"}, interceptors=[interceptor2]))
    clone.http = httpx2.AsyncClient(
        transport=mock_transport,
        base_url=clone.http.base_url,
        headers=clone.http.headers,
        timeout=clone.http.timeout,
        event_hooks=clone.http.event_hooks,
    )

    resp = await clone.get("/clone")
    assert resp.status_code == 200
    assert not interceptor1.request_called
    assert interceptor2.request_called


def test_interceptors_returns_read_only_copy():
    interceptor1 = DummyAsyncInterceptor()
    client = Client(ClientOptions(interceptors=[interceptor1]))

    assert client.interceptors == (interceptor1,)


def test_middlewares_returns_read_only_copy():
    middleware = RecordingMiddleware("middleware", [])
    client = Client()
    client.use(middleware)

    assert client.middlewares == (middleware,)


def test_clone_copies_interceptor_list_independently():
    interceptor1 = DummyAsyncInterceptor()
    client = Client(ClientOptions(interceptors=[interceptor1]))

    clone = client.clone()
    interceptor2 = DummyAsyncInterceptor()
    clone.use_interceptor(interceptor2)

    assert client.interceptors == (interceptor1,)
    assert clone.interceptors == (interceptor1, interceptor2)
    assert client.interceptors is not clone.interceptors


def test_clone_copies_middleware_list_independently():
    middleware1 = RecordingMiddleware("one", [])
    client = Client()
    client.use(middleware1)

    clone = client.clone()
    middleware2 = RecordingMiddleware("two", [])
    clone.use(middleware2)

    assert client.middlewares == (middleware1,)
    assert clone.middlewares == (middleware1, middleware2)
    assert client.middlewares is not clone.middlewares


def test_middlewares_support_deduping_by_inspection():
    middleware = RecordingMiddleware("one", [])
    client = Client()
    client.use(middleware)

    if not any(isinstance(existing, RecordingMiddleware) for existing in client.middlewares):
        client.use(RecordingMiddleware("duplicate", []))

    assert client.middlewares == (middleware,)


def test_clone_reuses_underlying_http_client_when_requested():
    client = Client(ClientOptions(base_url="https://example.com"))

    clone = client.clone(share_http=True)

    assert clone is not client
    assert clone.http is client.http


@pytest.mark.asyncio
async def test_middleware_runs_in_insertion_order_with_first_outermost(use_mock_transport):
    events: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        events.append("terminal")
        return httpx2.Response(200, json={"ok": True}, headers={"content-type": "application/json"})

    client = create_mock_client(httpx2.MockTransport(handler))
    client.use(RecordingMiddleware("one", events))
    client.use(RecordingMiddleware("two", events))

    await client.get("/ordered")

    assert events == [
        "one:before:GET",
        "two:before:GET",
        "terminal",
        "two:after:200",
        "one:after:200",
    ]


@pytest.mark.asyncio
async def test_middleware_can_mutate_headers_and_kwargs(use_mock_transport):
    def handler(request: httpx2.Request) -> httpx2.Response:
        return httpx2.Response(
            200,
            json={
                "header": request.headers["x-middleware"],
                "extension": request.extensions["middleware"],
            },
            headers={"content-type": "application/json"},
        )

    class MutatingMiddleware:
        async def send(self, context: MiddlewareContext, next: MiddlewareNext) -> httpx2.Response:
            context.headers["X-Middleware"] = "header-value"
            context.kwargs["extensions"] = {"middleware": "extension-value"}
            return await next()

    client = create_mock_client(httpx2.MockTransport(handler))
    client.use(MutatingMiddleware())

    response = await client.get("/mutated")

    assert response.json() == {"header": "header-value", "extension": "extension-value"}


@pytest.mark.asyncio
async def test_middleware_can_short_circuit_response(use_mock_transport):
    class ShortCircuitMiddleware:
        def send(self, context: MiddlewareContext, next: MiddlewareNext) -> httpx2.Response:
            return httpx2.Response(204)

    client = create_mock_client(httpx2.MockTransport(lambda request: httpx2.Response(500)))
    client.use(ShortCircuitMiddleware())

    response = await client.get("/short-circuit")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_middleware_observes_and_propagates_terminal_errors(use_mock_transport):
    events: list[str] = []
    error = RuntimeError("boom")

    def handler(request: httpx2.Request) -> httpx2.Response:
        raise error

    class ErrorRecordingMiddleware:
        async def send(self, context: MiddlewareContext, next: MiddlewareNext) -> httpx2.Response:
            try:
                return await next()
            except Exception as exception:
                events.append(str(exception))
                raise

    client = create_mock_client(httpx2.MockTransport(handler))
    client.use(ErrorRecordingMiddleware())

    with pytest.raises(RuntimeError, match="boom"):
        await client.get("/error")

    assert events == ["boom"]


@pytest.mark.asyncio
async def test_middleware_runs_around_existing_interceptors(mock_transport):
    events: list[str] = []

    class RecordingInterceptor(Interceptor):
        def request(self, ctx: InterceptorRequestContext) -> None:
            events.append("interceptor:request")

        def response(self, ctx: InterceptorResponseContext) -> None:
            events.append("interceptor:response")

    class EventMiddleware:
        async def send(self, context: MiddlewareContext, next: MiddlewareNext) -> httpx2.Response:
            events.append("middleware:before")
            response = await next()
            events.append("middleware:after")
            return response

    client = create_mock_client(
        mock_transport, ClientOptions(base_url="https://example.com", interceptors=[RecordingInterceptor()])
    )
    client.use(EventMiddleware())

    await client.get("/with-interceptors")

    assert events == ["middleware:before", "interceptor:request", "interceptor:response", "middleware:after"]


@pytest.mark.asyncio
async def test_request_metadata_is_not_sent_over_wire(use_mock_transport):
    captured: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        captured.append(request)
        return httpx2.Response(200, json={"ok": True}, headers={"content-type": "application/json"})

    class MetadataMiddleware:
        def __init__(self) -> None:
            self.metadata: object | None = None

        async def send(self, context: MiddlewareContext, next: MiddlewareNext) -> httpx2.Response:
            self.metadata = context.metadata
            return await next()

    metadata = object()
    middleware = MetadataMiddleware()
    client = create_mock_client(httpx2.MockTransport(handler))
    client.use(middleware)

    await client.get("/metadata", _metadata=metadata)

    assert middleware.metadata is metadata
    request = captured[0]
    assert "_metadata" not in str(request.url)
    assert "_metadata" not in request.headers
    assert "_metadata" not in request.extensions


def test_clone_uses_current_token_value():
    client = Client(ClientOptions(token="original-token"))
    client.token = None

    clone = client.clone()

    assert clone.token is None


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
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            token=token,
        ),
    )
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
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            token=async_none_factory,
        ),
    )
    resp = await client.get("/token-test")
    data = resp.json()
    assert "authorization" not in data["headers"]


@pytest.mark.asyncio
async def test_explicit_authorization_header_wins_over_default_token(mock_transport):
    client = create_mock_client(mock_transport, ClientOptions(base_url="https://example.com", token="default-token"))

    resp = await client.get("/token-test", headers={"Authorization": "******"})
    data = resp.json()

    assert data["headers"]["authorization"] == "******"


@pytest.mark.asyncio
async def test_default_authorization_header_bypasses_token_resolution(mock_transport):
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            headers={"Authorization": "******"},
            token=failing_token_factory,
        ),
    )
    resp = await client.get("/token-test")
    data = resp.json()

    assert data["headers"]["authorization"] == "******"


# Test token factory that raises an exception
def failing_token_factory() -> str:
    raise ValueError("Token factory failed")


@pytest.mark.asyncio
async def test_failing_token_factory(mock_transport):
    client = create_mock_client(
        mock_transport,
        ClientOptions(
            base_url="https://example.com",
            token=failing_token_factory,
        ),
    )
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
