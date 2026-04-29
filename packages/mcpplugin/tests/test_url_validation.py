"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import AsyncMock, patch

import pytest
from microsoft_teams.mcpplugin.url_validation import (
    UrlValidationError,
    UrlValidationParams,
    is_private_address,
    validate_mcp_server_url,
)

RESOLVE_HOST = "microsoft_teams.mcpplugin.url_validation._resolve_host"


@pytest.mark.parametrize(
    "address,expected",
    [
        ("127.0.0.1", True),
        ("10.0.0.1", True),
        ("10.255.255.255", True),
        ("172.16.0.1", True),
        ("172.31.255.255", True),
        ("192.168.1.1", True),
        ("169.254.169.254", True),
        ("0.0.0.0", True),
        ("0.255.255.255", True),
        ("100.64.0.1", True),
        ("100.127.255.254", True),
        ("100.63.255.255", False),
        ("100.128.0.1", False),
        ("224.0.0.1", True),
        ("239.255.255.255", True),
        ("240.0.0.1", True),
        ("255.255.255.255", True),
        ("8.8.8.8", False),
        ("1.1.1.1", False),
        ("172.15.0.1", False),
        ("172.32.0.1", False),
        ("::1", True),
        ("fc00::1", True),
        ("fd00::1", True),
        ("fe80::1", True),
        ("fec0::1", True),
        ("::", True),
        ("2001:4860:4860::8888", False),
        ("::ffff:127.0.0.1", True),
        ("::ffff:8.8.8.8", False),
        ("not-an-ip", True),
    ],
)
def test_is_private_address(address: str, expected: bool) -> None:
    assert is_private_address(address) == expected


@pytest.mark.asyncio
async def test_rejects_unparseable_url() -> None:
    with pytest.raises(UrlValidationError):
        await validate_mcp_server_url("not a url")


@pytest.mark.asyncio
async def test_rejects_non_http_schemes() -> None:
    with pytest.raises(UrlValidationError, match="scheme"):
        await validate_mcp_server_url("file:///etc/passwd")
    with pytest.raises(UrlValidationError, match="scheme"):
        await validate_mcp_server_url("ftp://example.com/x")


@pytest.mark.asyncio
async def test_accepts_public_url_with_public_dns() -> None:
    with patch(RESOLVE_HOST, new=AsyncMock(return_value=["8.8.8.8"])):
        result = await validate_mcp_server_url("https://example.com/mcp")
    assert result == "https://example.com/mcp"


@pytest.mark.asyncio
async def test_rejects_url_resolving_to_private_ip() -> None:
    with patch(RESOLVE_HOST, new=AsyncMock(return_value=["10.0.0.5"])):
        with pytest.raises(UrlValidationError, match="private or loopback"):
            await validate_mcp_server_url("https://internal.example.com/mcp")


@pytest.mark.asyncio
async def test_rejects_when_any_resolved_address_is_private() -> None:
    with patch(RESOLVE_HOST, new=AsyncMock(return_value=["8.8.8.8", "192.168.1.1"])):
        with pytest.raises(UrlValidationError, match="private or loopback"):
            await validate_mcp_server_url("https://mixed.example.com/mcp")


@pytest.mark.asyncio
async def test_rejects_ip_literal_private() -> None:
    # _resolve_host short-circuits for IP literals (no DNS call), so let the real
    # implementation run; rejection should still fire from the private-IP check.
    with pytest.raises(UrlValidationError, match="private or loopback"):
        await validate_mcp_server_url("http://127.0.0.1:3000")


@pytest.mark.asyncio
async def test_accepts_private_ip_when_allow_private_network() -> None:
    result = await validate_mcp_server_url(
        "http://127.0.0.1:3000",
        UrlValidationParams(allow_private_network=True),
    )
    assert result == "http://127.0.0.1:3000"


@pytest.mark.asyncio
async def test_rejects_unspecified_ipv4_even_when_allow_private_network() -> None:
    with pytest.raises(UrlValidationError, match="unspecified"):
        await validate_mcp_server_url(
            "http://0.0.0.0:3000",
            UrlValidationParams(allow_private_network=True),
        )


@pytest.mark.asyncio
async def test_rejects_unspecified_ipv6_even_when_allow_private_network() -> None:
    with pytest.raises(UrlValidationError, match="unspecified"):
        await validate_mcp_server_url(
            "http://[::]:3000",
            UrlValidationParams(allow_private_network=True),
        )


@pytest.mark.asyncio
async def test_accepts_private_hostname_when_allow_private_network_skips_dns() -> None:
    resolve = AsyncMock()
    with patch(RESOLVE_HOST, new=resolve):
        result = await validate_mcp_server_url(
            "https://internal.example.com/mcp",
            UrlValidationParams(allow_private_network=True),
        )
    assert result == "https://internal.example.com/mcp"
    resolve.assert_not_called()


@pytest.mark.asyncio
async def test_validate_url_sync_fully_replaces_default_checks() -> None:
    seen: list[str] = []

    def validator(url: str) -> bool:
        seen.append(url)
        return True

    result = await validate_mcp_server_url(
        "file:///etc/passwd",
        UrlValidationParams(validate_url=validator),
    )
    assert result == "file:///etc/passwd"
    assert seen == ["file:///etc/passwd"]


@pytest.mark.asyncio
async def test_validate_url_async_replaces_default_checks() -> None:
    async def validator(url: str) -> bool:
        return "example" in url

    result = await validate_mcp_server_url(
        "https://example.com/mcp",
        UrlValidationParams(validate_url=validator),
    )
    assert result == "https://example.com/mcp"


@pytest.mark.asyncio
async def test_validate_url_rejects_when_returning_false() -> None:
    with pytest.raises(UrlValidationError, match="rejected by validate_url"):
        await validate_mcp_server_url(
            "https://example.com/mcp",
            UrlValidationParams(validate_url=lambda _url: False),
        )


@pytest.mark.asyncio
async def test_rejects_when_dns_lookup_fails() -> None:
    # _resolve_host wraps socket.gaierror as UrlValidationError; verify the
    # caller surfaces that rather than swallowing it.
    with patch(
        RESOLVE_HOST,
        new=AsyncMock(side_effect=UrlValidationError("Could not resolve nonexistent.invalid")),
    ):
        with pytest.raises(UrlValidationError, match="Could not resolve"):
            await validate_mcp_server_url("https://nonexistent.invalid/mcp")


@pytest.mark.asyncio
async def test_rejects_when_dns_returns_empty_list() -> None:
    with patch(RESOLVE_HOST, new=AsyncMock(return_value=[])):
        with pytest.raises(UrlValidationError, match="did not resolve"):
            await validate_mcp_server_url("https://example.com/mcp")


@pytest.mark.asyncio
async def test_propagates_exceptions_from_validate_url() -> None:
    def boom(_url: str) -> bool:
        raise RuntimeError("custom failure")

    with pytest.raises(RuntimeError, match="custom failure"):
        await validate_mcp_server_url(
            "https://example.com/mcp",
            UrlValidationParams(validate_url=boom),
        )
