"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Optional

import httpx
from microsoft_teams.api import ConversationType

from .errors import FileScopeNotSupportedError, FileUrlExpiredError


@dataclass
class FileFetchTarget:
    """The minimal file description the download dispatcher needs to open a byte stream."""

    scope: ConversationType
    """Conversation scope; the dispatcher is keyed on this."""

    download_url: Optional[str] = None
    """Short-lived, pre-authorized download URL (personal scope)."""

    content_type: Optional[str] = None
    """MIME type reported by the incoming file, used as a fallback when the response omits one."""


@dataclass
class OpenedFileStream:
    """A freshly opened, single-consumption byte stream plus the metadata resolved while opening it."""

    chunks: AsyncIterator[bytes]
    """The raw response body stream. Uncapped; the caller bounds it."""

    source_url: str
    """The URL the bytes were actually fetched from."""

    content_type: str
    """MIME type resolved from the response, falling back to the incoming file's."""


@asynccontextmanager
async def open_file_stream(
    target: FileFetchTarget,
    *,
    prior_fetch_succeeded: bool = False,
    client: Optional[httpx.AsyncClient] = None,
) -> AsyncIterator[OpenedFileStream]:
    """
    Open a byte stream for an inbound file, keyed on its conversation scope so every scope's receive path extends this
    one place rather than branching in callers.

    Only `personal` is implemented; `groupChat`/`channel` (and any future scope) raise `FileScopeNotSupportedError`
    until their Graph receive path lands.
    """
    if target.scope != "personal":
        raise FileScopeNotSupportedError(str(target.scope))

    async with _open_personal_file_stream(target, prior_fetch_succeeded=prior_fetch_succeeded, client=client) as opened:
        yield opened


@asynccontextmanager
async def _open_personal_file_stream(
    target: FileFetchTarget,
    *,
    prior_fetch_succeeded: bool,
    client: Optional[httpx.AsyncClient],
) -> AsyncIterator[OpenedFileStream]:
    url = target.download_url

    if not url:
        raise RuntimeError("cannot download personal file: no download URL is available")

    owns_client = client is None
    http = client or httpx.AsyncClient()

    try:
        # Plain GET with no bearer token: the download URL embeds its own `tempauth` credential, and attaching a
        # credential can get the request rejected.
        async with http.stream("GET", url) as response:
            if response.status_code in (401, 403):
                raise FileUrlExpiredError("reread" if prior_fetch_succeeded else "first_fetch")

            if not response.is_success:
                raise RuntimeError(f"failed to download file: {response.status_code} {response.reason_phrase}".strip())

            content_type = response.headers.get("content-type") or target.content_type or "application/octet-stream"
            yield OpenedFileStream(chunks=response.aiter_bytes(), source_url=url, content_type=content_type)
    finally:
        if owns_client:
            await http.aclose()


async def collect_stream(chunks: AsyncIterator[bytes]) -> bytes:
    """Read a byte stream to completion into a single `bytes` object."""
    buffer = bytearray()

    async for chunk in chunks:
        buffer.extend(chunk)

    return bytes(buffer)
