"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import ipaddress
import logging
import re
from dataclasses import dataclass
from inspect import isawaitable
from typing import Awaitable, Callable, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_CGNAT_NETWORK = ipaddress.IPv4Network("100.64.0.0/10")
_IPV6_SITE_LOCAL = ipaddress.IPv6Network("fec0::/10")
_CREDS_PATTERN = re.compile(r"(\b[a-z][a-z0-9+.-]*://)[^@/?#]*@", re.IGNORECASE)


def _redact_creds(url: str) -> str:
    return _CREDS_PATTERN.sub(r"\1[REDACTED]@", url)


class UrlValidationError(ValueError):
    """Raised when an MCP server URL fails validation."""


@dataclass
class UrlValidationParams:
    """Parameters controlling MCP server URL validation."""

    allow_private_network: bool = False
    validate_url: Optional[Callable[[str], Union[bool, Awaitable[bool]]]] = None


async def validate_mcp_server_url(url: str, params: Optional[UrlValidationParams] = None) -> str:
    """
    Validate a URL destined for an MCP server connection.

    When ``validate_url`` is provided, it fully replaces the default checks.
    Otherwise the default policy rejects non-http(s) schemes, and (unless
    ``allow_private_network`` is True) rejects URLs whose hostname resolves
    to a private / loopback / link-local address.

    Returns the original URL on success. Raises :class:`UrlValidationError`
    on rejection.
    """
    params = params or UrlValidationParams()

    try:
        parsed = urlparse(url)
    except ValueError as err:
        raise UrlValidationError(f"Invalid URL: {_redact_creds(url)!r}") from err

    if not parsed.scheme:
        raise UrlValidationError(f"Invalid URL: {_redact_creds(url)!r}")

    if params.validate_url is not None:
        result = params.validate_url(url)
        if isawaitable(result):
            result = await result
        if not result:
            raise UrlValidationError(f"URL rejected by validate_url: {_redact_creds(url)}")
        return url

    if parsed.scheme not in ("http", "https"):
        raise UrlValidationError(f"URL scheme {parsed.scheme!r} is not allowed; must be http or https")

    if not parsed.hostname:
        raise UrlValidationError(f"Invalid URL: {_redact_creds(url)!r}")

    # Always reject unspecified addresses (0.0.0.0 / ::) — even with allow_private_network.
    # These aren't valid destinations and route to the local host on some platforms.
    try:
        literal_ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        literal_ip = None
    if literal_ip is not None and literal_ip.is_unspecified:
        raise UrlValidationError(
            f"URL {_redact_creds(url)} resolves to unspecified address {parsed.hostname}"
        )

    if params.allow_private_network:
        return url

    addresses = await _resolve_host(parsed.hostname)
    if not addresses:
        raise UrlValidationError(f"URL {_redact_creds(url)} did not resolve to any address")
    for address in addresses:
        if is_private_address(address):
            raise UrlValidationError(
                f"URL {_redact_creds(url)} resolves to private or loopback address {address}; "
                "set allow_private_network=True to bypass"
            )

    return url


def is_private_address(address: str) -> bool:
    """True if an IP address is loopback, private, link-local, unspecified, multicast, CGNAT, or IPv6 site-local."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True  # Unknown: fail closed.
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_unspecified
        or ip.is_multicast  # 224.0.0.0/4 IPv4, ff00::/8 IPv6
    ):
        return True
    # CGNAT (RFC 6598, 100.64.0.0/10) — Python's is_private didn't classify it
    # until 3.13; keep the explicit check for 3.12 compatibility.
    if isinstance(ip, ipaddress.IPv4Address) and ip in _CGNAT_NETWORK:
        return True
    # RFC 4291 deprecated IPv6 site-local (fec0::/10). Python's is_private does
    # not classify it, but we reject for parity with the C# SDK.
    if isinstance(ip, ipaddress.IPv6Address) and ip in _IPV6_SITE_LOCAL:
        return True
    return False


async def _resolve_host(host: str) -> List[str]:
    """Resolve a hostname to its IP addresses; short-circuit IP literals."""
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass

    loop = asyncio.get_running_loop()
    try:
        results = await loop.getaddrinfo(host, None)
    except (OSError, UnicodeError) as err:
        raise UrlValidationError(f"Could not resolve {host}: {err}") from err

    return list({entry[4][0] for entry in results})
