"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# The two-step handshake that turns bot credentials into a WebSocket URL.
#
# First the Teams service is asked where to connect and for a connection token; then
# SignalR is negotiated at that address, following any redirects it returns.
#
# Every URL crossing this module is checked by :func:`assert_secure_url` before it is
# used or a token is attached to it, so a downgraded or redirected endpoint cannot be
# handed a bearer token over cleartext.

import asyncio
import ipaddress
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Awaitable, Callable, Mapping, Optional, cast
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

logger = logging.getLogger(__name__)

DEFAULT_NEGOTIATE_TIMEOUT = 15.0
"""Seconds to wait for a negotiate HTTP response before giving up."""

MAX_SIGNALR_NEGOTIATE_REDIRECTS = 10


@dataclass(frozen=True)
class NegotiateResult:
    """Successful negotiate response: where to connect and the token to connect with."""

    url: str
    access_token: str
    expires_in: float = 0
    """Token lifetime in seconds; ``0`` when the service does not report one."""


@dataclass(frozen=True)
class SignalREndpoint:
    """Final WebSocket URL and token after following any negotiate redirects."""

    url: str
    access_token: str


class NegotiateError(RuntimeError):
    """
    A negotiate step failed.

    ``retry_after`` carries the service's ``Retry-After`` when it sent one, so the
    supervisor can honour throttling instead of applying its own backoff.
    """

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


def assert_secure_url(url: str, *, purpose: str, websocket_allowed: bool = False) -> None:
    """
    Reject a URL that would carry credentials over cleartext.

    ``https`` (and ``wss`` where allowed) always pass. Cleartext passes only for
    loopback, which keeps local testing workable without opening a downgrade path.
    """
    try:
        parsed = urlsplit(url)
        _ = parsed.port
    except ValueError as error:
        raise ValueError(f"Socket Mode {purpose} URL is not a valid URL: {url}") from error

    allowed_secure = {"https"}
    allowed_loopback = {"http"}
    if websocket_allowed:
        allowed_secure.add("wss")
        allowed_loopback.add("ws")
    if parsed.scheme in allowed_secure and parsed.hostname:
        return
    if parsed.scheme in allowed_loopback and _is_loopback(parsed.hostname):
        return
    schemes = "https/wss" if websocket_allowed else "https"
    host = parsed.hostname or "(missing host)"
    raise ValueError(
        f"Socket Mode {purpose} URL must use {schemes} (got {parsed.scheme or '(missing scheme)'}://{host})"
    )


def _is_loopback(host: Optional[str]) -> bool:
    if host is None:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _safe_url(url: str) -> str:
    """
    Scheme, host and path only, for log output.

    Negotiate URLs carry ``access_token`` in their query string, so the query is dropped
    rather than redacted field by field, and any ``user:pass@`` prefix is stripped.
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "(unparsable url)"
    netloc = parsed.netloc.rsplit("@", 1)[-1] or "(missing host)"
    return f"{parsed.scheme or '(missing scheme)'}://{netloc}{parsed.path}"


async def negotiate_service(
    negotiate_url: str,
    get_bot_token: Callable[[], Awaitable[str]],
    *,
    http_client: Optional[httpx.AsyncClient] = None,
    timeout: float = DEFAULT_NEGOTIATE_TIMEOUT,
) -> NegotiateResult:
    token = await get_bot_token()
    if not token:
        raise NegotiateError(
            "Socket Mode negotiate has no bot token; configure application credentials or a token provider"
        )
    assert_secure_url(negotiate_url, purpose="negotiate")

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient()
    try:
        logger.debug("Socket Mode service negotiate requesting %s", _safe_url(negotiate_url))
        async with asyncio.timeout(timeout):
            response = await client.post(
                negotiate_url,
                headers={"Authorization": f"Bearer {token}"},
            )
        if not response.is_success:
            body = response.text[:500]
            retry_after = _parse_retry_after(response.headers)
            logger.warning(
                "Socket Mode service negotiate failed: HTTP %d (retry_after=%s)",
                response.status_code,
                retry_after,
            )
            raise NegotiateError(
                f"Socket Mode negotiate failed: HTTP {response.status_code} {body}",
                retry_after,
            )
        payload = _response_object(response, "Socket Mode negotiate")
        url = payload.get("url")
        access_token = payload.get("accessToken")
        expires_in = payload.get("expiresIn", 0)
        if not isinstance(url, str) or not url or not isinstance(access_token, str) or not access_token:
            raise NegotiateError("Socket Mode negotiate response missing url/accessToken")
        assert_secure_url(url, purpose="negotiated SignalR", websocket_allowed=True)
        if not isinstance(expires_in, (int, float)) or isinstance(expires_in, bool):
            expires_in = 0
        logger.debug(
            "Socket Mode service negotiate resolved %s (expires_in=%ss)",
            _safe_url(url),
            expires_in or "unreported",
        )
        return NegotiateResult(url=url, access_token=access_token, expires_in=float(expires_in))
    finally:
        if owns_client:
            await client.aclose()


async def negotiate_signalr(
    hub_url: str,
    access_token: str,
    *,
    http_client: Optional[httpx.AsyncClient] = None,
    timeout: float = DEFAULT_NEGOTIATE_TIMEOUT,
) -> SignalREndpoint:
    assert_secure_url(hub_url, purpose="negotiated SignalR", websocket_allowed=True)
    if urlsplit(hub_url).scheme in {"ws", "wss"}:
        return SignalREndpoint(url=_with_query(hub_url, {"access_token": access_token}), access_token=access_token)

    owns_client = http_client is None
    client = http_client or httpx.AsyncClient()
    current_url = hub_url
    current_token = access_token
    try:
        for hop in range(MAX_SIGNALR_NEGOTIATE_REDIRECTS + 1):
            assert_secure_url(current_url, purpose="SignalR redirect", websocket_allowed=True)
            if urlsplit(current_url).scheme in {"ws", "wss"}:
                return SignalREndpoint(
                    url=_with_query(current_url, {"access_token": current_token}),
                    access_token=current_token,
                )
            negotiate_url = _signalr_negotiate_url(current_url)
            logger.debug("SignalR negotiate hop %d requesting %s", hop, _safe_url(negotiate_url))
            async with asyncio.timeout(timeout):
                response = await client.post(
                    negotiate_url,
                    headers={"Authorization": f"Bearer {current_token}"},
                )
            if not response.is_success:
                retry_after = _parse_retry_after(response.headers)
                logger.warning(
                    "SignalR negotiate failed: HTTP %d (retry_after=%s)",
                    response.status_code,
                    retry_after,
                )
                raise NegotiateError(
                    f"SignalR negotiate failed: HTTP {response.status_code} {response.text[:500]}",
                    retry_after,
                )
            payload = _response_object(response, "SignalR negotiate")
            if isinstance(payload.get("error"), str):
                raise NegotiateError(f"SignalR negotiate failed: {payload['error']}")

            redirect_url = payload.get("url")
            if isinstance(redirect_url, str) and redirect_url:
                assert_secure_url(redirect_url, purpose="SignalR redirect", websocket_allowed=True)
                redirect_token = payload.get("accessToken")
                if redirect_token is not None and (not isinstance(redirect_token, str) or not redirect_token):
                    raise NegotiateError("SignalR negotiate returned an invalid accessToken")
                current_url = redirect_url
                if isinstance(redirect_token, str):
                    current_token = redirect_token
                logger.debug(
                    "SignalR negotiate redirected to %s (token_replaced=%s)",
                    _safe_url(redirect_url),
                    isinstance(redirect_token, str),
                )
                continue

            connection_token = payload.get("connectionToken") or payload.get("connectionId")
            if not isinstance(connection_token, str) or not connection_token:
                raise NegotiateError("SignalR negotiate response missing connectionToken")
            _require_text_websocket(payload.get("availableTransports"))
            websocket_url = _to_websocket_url(current_url, connection_token, current_token)
            logger.debug("SignalR negotiate resolved WebSocket endpoint %s", _safe_url(websocket_url))
            return SignalREndpoint(url=websocket_url, access_token=current_token)
        logger.warning("SignalR negotiate exceeded %d redirects", MAX_SIGNALR_NEGOTIATE_REDIRECTS)
        raise NegotiateError("SignalR negotiate exceeded the redirect limit")
    finally:
        if owns_client:
            await client.aclose()


def _response_object(response: httpx.Response, operation: str) -> dict[str, object]:
    """
    Decode a negotiate response body, rejecting anything that is not a JSON object.

    The key type needs no check: JSON object keys are strings by definition, so the decoder
    cannot produce anything else.
    """
    try:
        payload: object = response.json()
    except ValueError as error:
        raise NegotiateError(f"{operation} response was not valid JSON") from error
    if not isinstance(payload, dict):
        raise NegotiateError(f"{operation} response must be a JSON object")
    return cast(dict[str, object], payload)


def _signalr_negotiate_url(hub_url: str) -> str:
    parsed = urlsplit(hub_url)
    path = f"{parsed.path.rstrip('/')}/negotiate"
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query["negotiateVersion"] = "1"
    return urlunsplit((parsed.scheme, parsed.netloc, path, urlencode(query), ""))


def _to_websocket_url(hub_url: str, connection_token: str, access_token: str) -> str:
    parsed = urlsplit(hub_url)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    url = urlunsplit((scheme, parsed.netloc, parsed.path, parsed.query, ""))
    return _with_query(url, {"id": connection_token, "access_token": access_token})


def _with_query(url: str, values: Mapping[str, str]) -> str:
    parsed = urlsplit(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(values)
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def _require_text_websocket(value: object) -> None:
    if not isinstance(value, list):
        raise NegotiateError("SignalR negotiate response missing availableTransports")
    for item in cast(list[object], value):
        if not isinstance(item, dict):
            continue
        transport = cast(Mapping[str, object], item)
        if transport.get("transport") != "WebSockets":
            continue
        formats = transport.get("transferFormats")
        if isinstance(formats, list) and "Text" in formats:
            return
    raise NegotiateError("SignalR negotiate did not offer the WebSockets Text transport")


def _parse_retry_after(headers: httpx.Headers) -> Optional[float]:
    raw: Optional[str] = headers.get("retry-after")
    if not raw:
        return None
    try:
        return max(0.0, float(raw))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(raw)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None
