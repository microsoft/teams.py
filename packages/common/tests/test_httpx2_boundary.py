"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
from collections.abc import AsyncIterator
from io import BytesIO

import httpx2
import pytest
from microsoft_teams.common.http import Client, ClientOptions
from microsoft_teams.common.http.request_types import QueryParamTypes, RequestContent, RequestData, RequestFiles


async def test_sdk_constructs_httpx2_with_existing_timeout_and_clone_contract():
    client = Client(ClientOptions(headers={"User-Agent": "teams-test"}))
    clone = client.clone()
    shared = client.clone(share_http=True)
    try:
        assert isinstance(client.http, httpx2.AsyncClient)
        assert client.http.timeout == httpx2.Timeout(None)
        assert clone.http is not client.http
        assert shared.http is client.http
        assert clone.http.headers["user-agent"] == "teams-test"
    finally:
        await clone.http.aclose()
        await client.http.aclose()


async def test_status_errors_preserve_request_and_response():
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(403))) as raw:
        client = Client(_http=raw)
        with pytest.raises(httpx2.HTTPStatusError) as sdk_error:
            await client.get("https://example.test/sdk")

        assert isinstance(sdk_error.value.request, httpx2.Request)
        assert isinstance(sdk_error.value.response, httpx2.Response)
        assert str(sdk_error.value.request.url) == "https://example.test/sdk"
        assert sdk_error.value.response.status_code == 403
        assert not raw.is_closed


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def test_dispatch_preserves_methods_query_headers_and_timeout(method: str):
    requests: list[httpx2.Request] = []

    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, json={})

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(respond)) as raw:
        client = Client(ClientOptions(headers={"X-Default": "default"}, token="bot-token"), _http=raw)
        response = await client.request(
            method,
            "https://example.test/resource",
            params=[("item", "one"), ("item", "two")],
            headers={"X-Request": "request"},
            timeout=2,
        )
        assert isinstance(response, httpx2.Response)
        request = requests[0]
        assert request.method == method
        assert request.url.params.get_list("item") == ["one", "two"]
        assert request.headers["authorization"] == "Bearer bot-token"
        assert request.headers["x-default"] == "default"
        assert request.headers["x-request"] == "request"
        assert request.extensions["timeout"] == dict(connect=2, read=2, write=2, pool=2)


async def test_sdk_query_types_cover_public_httpx2_input_shapes():
    params_cases: list[QueryParamTypes] = [
        httpx2.QueryParams("item=one&item=two"),
        {"item": ["one", "two"], "count": 2, "enabled": True, "missing": None},
        [("item", "one"), ("item", "two"), ("count", 2.5)],
        (("item", "one"), ("item", "two")),
        "item=one&item=two",
        b"item=one&item=two",
    ]
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(200))) as raw:
        client = Client(_http=raw)
        for params in params_cases:
            response = await client.get("https://example.test/query", params=params)
            expected = httpx2.Request("GET", "https://example.test/query", params=params)
            assert response.request.url == expected.url


async def test_sdk_multipart_types_cover_files_tuples_headers_and_repeated_fields():
    with BytesIO(b"payload") as file:
        files_cases: list[RequestFiles] = [
            {"upload": file},
            {"upload": b"payload"},
            {"upload": "payload"},
            {"upload": ("test.txt", file)},
            {"upload": (None, b"payload")},
            {"upload": ("test.txt", b"payload", "text/plain")},
            {"upload": ("test.txt", b"payload", None)},
            {"upload": ("test.txt", b"payload", "text/plain", {"X-Part": "fixture"})},
            [("upload", ("first.txt", b"payload")), ("upload", ("second.txt", b"payload"))],
        ]
        async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(200))) as raw:
            client = Client(_http=raw)
            requests: list[httpx2.Request] = []
            for files in files_cases:
                file.seek(0)
                response = await client.post("https://example.test/upload", data={"field": "value"}, files=files)
                requests.append(response.request)
                assert b"\r\npayload\r\n" in response.request.content
                assert b"\r\nvalue\r\n" in response.request.content
                assert response.request.headers["content-type"].startswith("multipart/form-data; boundary=")
            assert b'filename="test.txt"' in requests[3].content
            assert b"X-Part: fixture" in requests[-2].content
            assert requests[-1].content.count(b'name="upload"') == 2


async def test_sdk_form_and_content_types_remain_assignable_to_httpx2():
    async def chunks() -> AsyncIterator[bytes]:
        yield b"pay"
        yield b"load"

    form: RequestData = {"item": ["one", "two"], "count": 2, "enabled": True, "missing": None}
    contents: list[RequestContent] = ["payload", b"payload", chunks()]
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(200))) as raw:
        client = Client(_http=raw)
        response = await client.post("https://example.test/form", data=form)
        expected = httpx2.Request("POST", "https://example.test/form", data=form)
        assert response.request.content == expected.content
        assert response.request.headers["content-type"] == "application/x-www-form-urlencoded"
        for content in contents:
            response = await client.post("https://example.test/content", content=content)
            assert response.request.content == b"payload"


@pytest.mark.parametrize("body", [b"", b'{"incomplete":'])
async def test_json_wrapper_retains_existing_empty_body_behavior(body: bytes):
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(lambda _: httpx2.Response(200, content=body))) as raw:
        response = await Client(_http=raw).get("https://example.test/json")
        if body:
            with pytest.raises(json.JSONDecodeError):
                response.json()
        else:
            assert response.json() == {}
