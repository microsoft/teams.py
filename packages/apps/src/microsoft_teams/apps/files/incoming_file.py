"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

import httpx
from microsoft_teams.api import ConversationType

from .download import FileFetchTarget, OpenedFileStream, collect_stream, open_file_stream
from .downloaded_file import DownloadedFile
from .types import FileSource


class IncomingFile:
    """
    A lazy handle to a file attached to the current inbound activity.

    Nothing is downloaded until a byte method is called. The handle stays live and holds no memoized bytes, so each of
    `stream()`/`download()`/`text()`/`save_as()` fetches afresh. For a personal file that re-fetch is bounded by the
    short-lived download URL lifetime and may hit its expiry; to read the same file several ways, call `download()`
    once and reuse the returned `DownloadedFile`.
    """

    unique_id: Optional[str]
    """
    The OneDrive/ODSP drive-item id when the platform reports it (`content.uniqueId`); the storage-specific locator a
    Graph fetch keys off. Present only when the wire provided it.
    """

    name: str
    """Display name including extension when known."""

    content_type: Optional[str]
    """MIME type when known."""

    extension: Optional[str]
    """
    File extension without the dot (e.g. `pdf`), taken from the platform-supplied `file_type`. Absent when the wire
    omits it.
    """

    scope: ConversationType
    """Conversation scope the file arrived in (the SDK's `ConversationType`)."""

    source: FileSource
    """Where the SDK found the file. Only `botActivity` is produced today."""

    web_url: Optional[str]
    """Web URL to the file in OneDrive/SharePoint when known."""

    raw: Any
    """The raw underlying attachment/graph object for escape-hatch access."""

    def __init__(
        self,
        *,
        name: str,
        scope: ConversationType,
        source: FileSource,
        unique_id: Optional[str] = None,
        content_type: Optional[str] = None,
        extension: Optional[str] = None,
        web_url: Optional[str] = None,
        raw: Any = None,
        download_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.name = name
        self.scope = scope
        self.source = source
        self.unique_id = unique_id
        self.content_type = content_type
        self.extension = extension
        self.web_url = web_url
        self.raw = raw
        self._download_url = download_url
        self._client = client
        self._prior_fetch_succeeded = False

    async def stream(self) -> AsyncIterator[bytes]:
        """
        Stream the bytes. Low-level primitive: yields the response body chunks directly from the fetch,
        single-consumption, not buffered or retained. Use for large files and pipelines (parse-as-you-go, pipe to
        disk). `download()` is built on this. Uncapped: the consumer bounds it by how much it reads.
        """
        async with self._open() as opened:
            async for chunk in opened.chunks:
                yield chunk

    async def download(self) -> DownloadedFile:
        """
        Fetch the whole file and buffer it into a `DownloadedFile` snapshot you own. Lazy and not memoized: calling
        again re-fetches. If you already hold a `DownloadedFile`, call its `save_as()` rather than this handle's, which
        would re-fetch.
        """
        async with self._open() as opened:
            data = await collect_stream(opened.chunks)
            return DownloadedFile(
                bytes=data,
                content_type=opened.content_type,
                filename=self.name,
                source_url=opened.source_url,
            )

    async def text(self, encoding: str = "utf-8") -> str:
        """
        Convenience: run `download()` then decode the bytes as UTF-8 (or a provided encoding). Re-fetches on each call
        (no memoized bytes); to read bytes several ways hold one `DownloadedFile` instead. No content-type check;
        decoding is lossy (invalid bytes become U+FFFD and never throw). For strict or binary-safe reads, use
        `download().bytes`.
        """
        downloaded = await self.download()
        return downloaded.text(encoding)

    async def save_as(self, path: str) -> None:
        """
        Stream the bytes straight to a local file path, so saving a large file never materializes it in memory.
        """
        async with self._open() as opened:
            file = await asyncio.to_thread(open, path, "wb")
            try:
                async for chunk in opened.chunks:
                    await asyncio.to_thread(file.write, chunk)
            finally:
                await asyncio.to_thread(file.close)

    @asynccontextmanager
    async def _open(self) -> AsyncIterator[OpenedFileStream]:
        async with open_file_stream(
            self._target(),
            prior_fetch_succeeded=self._prior_fetch_succeeded,
            client=self._client,
        ) as opened:
            self._prior_fetch_succeeded = True
            yield opened

    def _target(self) -> FileFetchTarget:
        return FileFetchTarget(
            scope=self.scope,
            download_url=self._download_url,
            content_type=self.content_type,
        )
