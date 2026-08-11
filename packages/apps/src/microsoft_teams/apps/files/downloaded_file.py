"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DownloadedFile:
    """
    A buffered, point-in-time snapshot of a downloaded file's bytes that the caller owns.

    Returned by `IncomingFile.download()`. The bytes are already in memory, so the convenience readers here are
    synchronous and never re-download.
    Because it is a snapshot, holding one and reusing it is the way to read the same file several ways without
    re-fetching through the live `IncomingFile` handle.
    """

    bytes: bytes
    """The file bytes, buffered from `stream()` read to completion."""

    content_type: str
    """MIME type resolved from the download response header, or the incoming file's metadata type if the
    response omits one. Falls back to `application/octet-stream` when neither provides a type, so this is
    never empty."""

    filename: str
    """Resolved filename."""

    source_url: str
    """The URL the bytes were actually fetched from."""

    def text(self, encoding: str = "utf-8") -> str:
        """
        Decode bytes as UTF-8 (or a provided encoding). No content-type check.
        Lossy: invalid bytes become the U+FFFD replacement character and never throw.
        For strict or binary-safe reads, use `bytes`.
        """
        return self.bytes.decode(encoding, errors="replace")

    async def save_as(self, path: str) -> None:
        """
        Write the already-buffered bytes to a local file path (no re-fetch, unlike `IncomingFile.save_as()` which
        streams a fresh download).
        """
        await asyncio.to_thread(Path(path).write_bytes, self.bytes)
