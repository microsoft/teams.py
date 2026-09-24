"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from typing import Optional
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from microsoft_teams.apps.socket_mode.negotiate import (
    NegotiateError,
    assert_secure_url,
    negotiate_service,
    negotiate_signalr,
)


@pytest.mark.asyncio
async def test_service_negotiate_authenticates_and_parses_result():
    seen_request: Optional[httpx.Request] = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal seen_request
        seen_request = request
        return httpx.Response(
            200,
            json={"url": "https://signalr.example/hub", "accessToken": "signalr-token", "expiresIn": 120},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await negotiate_service(
            "https://botapi.example/v3/websockets/connect",
            lambda: _token("bot-token"),
            http_client=client,
        )

    assert result.url == "https://signalr.example/hub"
    assert result.access_token == "signalr-token"
    assert result.expires_in == 120
    assert seen_request is not None
    assert seen_request.headers["authorization"] == "Bearer bot-token"


@pytest.mark.asyncio
async def test_service_negotiate_rejects_plaintext_before_sending_token():
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="must use https"):
            await negotiate_service(
                "http://botapi.example/v3/websockets/connect",
                lambda: _token("bot-token"),
                http_client=client,
            )

    assert calls == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:3978/v3/websockets/connect",
        "http://127.0.0.1:3978/v3/websockets/connect",
        "http://[::1]:3978/v3/websockets/connect",
        "ws://localhost:3978/hub",
    ],
)
def test_url_validation_allows_loopback_plaintext(url: str):
    assert_secure_url(url, purpose="test", websocket_allowed=url.startswith("ws"))


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost.example/hub",
        "ws://10.0.0.4/hub",
        "ftp://signalr.example/hub",
        "https:///missing-host",
    ],
)
def test_url_validation_rejects_insecure_or_invalid_destinations(url: str):
    with pytest.raises(ValueError, match="must use"):
        assert_secure_url(url, purpose="test", websocket_allowed=True)


@pytest.mark.asyncio
async def test_service_negotiate_exposes_retry_after():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down", headers={"Retry-After": "2.5"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NegotiateError) as raised:
            await negotiate_service(
                "https://botapi.example/v3/websockets/connect",
                lambda: _token("bot-token"),
                http_client=client,
            )

    assert raised.value.retry_after == 2.5


@pytest.mark.asyncio
async def test_service_negotiate_accepts_http_date_retry_after():
    retry_at = datetime.now(timezone.utc) + timedelta(seconds=30)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            429,
            text="slow down",
            headers={"Retry-After": format_datetime(retry_at, usegmt=True)},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NegotiateError) as raised:
            await negotiate_service(
                "https://botapi.example/v3/websockets/connect",
                lambda: _token("bot-token"),
                http_client=client,
            )

    assert raised.value.retry_after is not None
    assert 25 <= raised.value.retry_after <= 30


@pytest.mark.asyncio
async def test_service_negotiate_ignores_unparsable_retry_after():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down", headers={"Retry-After": "whenever"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NegotiateError) as raised:
            await negotiate_service(
                "https://botapi.example/v3/websockets/connect",
                lambda: _token("bot-token"),
                http_client=client,
            )

    assert raised.value.retry_after is None


@pytest.mark.asyncio
async def test_signalr_negotiate_builds_secure_websocket_url():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "connectionToken": "connection-token",
                "availableTransports": [
                    {"transport": "WebSockets", "transferFormats": ["Text", "Binary"]},
                ],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        endpoint = await negotiate_signalr(
            "https://signalr.example/client/?hub=teams",
            "signalr-token",
            http_client=client,
        )

    assert len(requests) == 1
    assert requests[0].url.path == "/client/negotiate"
    assert requests[0].url.params["negotiateVersion"] == "1"
    assert requests[0].headers["authorization"] == "Bearer signalr-token"
    parsed = urlsplit(endpoint.url)
    assert parsed.scheme == "wss"
    assert parse_qs(parsed.query) == {
        "hub": ["teams"],
        "id": ["connection-token"],
        "access_token": ["signalr-token"],
    }


@pytest.mark.asyncio
async def test_signalr_negotiate_rejects_insecure_redirect_before_following_it():
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"url": "http://attacker.example/hub", "accessToken": "secret"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError, match="must use"):
            await negotiate_signalr("https://signalr.example/hub", "token", http_client=client)

    assert calls == 1


@pytest.mark.asyncio
async def test_negotiate_logs_never_contain_tokens(caplog: pytest.LogCaptureFixture):
    """Negotiate URLs carry credentials in their query string; logs must not echo them."""
    bot_secret = "bot-secret-do-not-log"
    service_secret = "service-secret-do-not-log"
    redirect_secret = "redirect-secret-do-not-log"

    def service_handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "url": "https://signalr.example/hub?hub=teams",
                "accessToken": service_secret,
                "expiresIn": 120,
            },
        )

    hops = 0

    def signalr_handler(_: httpx.Request) -> httpx.Response:
        nonlocal hops
        hops += 1
        if hops == 1:
            return httpx.Response(
                200,
                json={"url": "https://signalr-2.example/hub", "accessToken": redirect_secret},
            )
        return httpx.Response(
            200,
            json={
                "connectionToken": "connection-token-secret",
                "availableTransports": [{"transport": "WebSockets", "transferFormats": ["Text"]}],
            },
        )

    with caplog.at_level(logging.DEBUG, logger="microsoft_teams.apps.socket_mode.negotiate"):
        async with httpx.AsyncClient(transport=httpx.MockTransport(service_handler)) as client:
            result = await negotiate_service(
                "https://botapi.example/v3/websockets/connect",
                lambda: _token(bot_secret),
                http_client=client,
            )
        async with httpx.AsyncClient(transport=httpx.MockTransport(signalr_handler)) as client:
            endpoint = await negotiate_signalr(result.url, result.access_token, http_client=client)

    # The flow really did produce a credential-bearing URL, so the assertions below are meaningful.
    assert service_secret in result.url or redirect_secret in endpoint.url
    assert "access_token" in urlsplit(endpoint.url).query

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert caplog.records, "expected negotiate to emit debug logs"
    for secret in (bot_secret, service_secret, redirect_secret, "connection-token-secret"):
        assert secret not in logged
    assert "access_token" not in logged
    # Hosts are still logged, so a failure remains diagnosable.
    assert "signalr-2.example" in logged


async def _token(value: str) -> str:
    return value
