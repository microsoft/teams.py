"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from inspect import isawaitable
from typing import Awaitable, Callable, List, Optional, Union
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


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
        raise UrlValidationError(f"Invalid URL: {url!r}") from err

    if not parsed.scheme:
        raise UrlValidationError(f"Invalid URL: {url!r}")

    if params.validate_url is not None:
        result = params.validate_url(url)
        if isawaitable(result):
            result = await result
        if not result:
            raise UrlValidationError(f"URL rejected by validate_url: {url}")
        return url

    if parsed.scheme not in ("http", "https"):
        raise UrlValidationError(f"URL scheme {parsed.scheme!r} is not allowed; must be http or https")

    if not parsed.hostname:
        raise UrlValidationError(f"Invalid URL: {url!r}")

    if params.allow_private_network:
        return url

    addresses = await _resolve_host(parsed.hostname)
    for address in addresses:
        if is_private_address(address):
            raise UrlValidationError(
                f"URL {url} resolves to private or loopback address {address}; set allow_private_network=True to bypass"
            )

    return url


def is_private_address(address: str) -> bool:
    """True if an IP address is loopback, private, link-local, or unspecified."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return True  # Unknown: fail closed.
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified


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
    except socket.gaierror as err:
        raise UrlValidationError(f"Could not resolve {host}: {err}") from err

    return list({entry[4][0] for entry in results})
