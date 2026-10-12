"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx
from microsoft_teams.api import ConversationType

from .download import (
    BotApiCredential,
    FileFetchTarget,
    GraphCredential,
    OpenedFileStream,
    collect_stream,
    open_file_stream,
)
from .downloaded_file import DownloadedFile
from .inline_image import inline_image_naming, sniff_image_format
from .types import AttachmentStyle, FileSource


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
    The ODSP/OneDrive identifier for the file when the platform reports it (`content.uniqueId`). Useful for
    correlation, dedup and logging, but not for retrieval: the Graph fetch resolves bytes from `content_url` through
    `/shares`, and this value arrives as a GUID, which is a SharePoint `listItemUniqueId` shape rather than a Graph
    `driveItem.id`. Present only when the wire provided it.
    Always `None` for inline images, which are not stored in OneDrive or SharePoint.
    """

    name: str
    """
    Display name including extension when known.
    An inline image has no name, so it is named `image-<attachment id>`.
    An extension is added only for PNG, JPEG, GIF, or WebP.
    Teams saves a pasted GIF as a static PNG, so the SDK cannot name or type it with confidence: it is listed as
    `.gif` and `image/gif` but downloads as a PNG.
    """

    content_type: Optional[str]
    """
    The file's MIME type when the source provides one. Always `None` for `botActivity` file attachments: a
    `file.download.info` attachment carries no MIME type, only the `file_type` extension surfaced as `extension`.
    Populated for sources that do carry one, such as a `graph` drive item. To learn the type of the bytes you actually
    received, read `DownloadedFile.content_type`, which is resolved from the download response.

    For an inline image, it is the type named by the format hint when that is PNG, JPEG, GIF, or WebP, otherwise
    `application/octet-stream`.
    Teams saves a pasted GIF as a static PNG, so the SDK cannot name or type it with confidence: it is listed as
    `.gif` and `image/gif` but downloads as a PNG.
    """

    extension: Optional[str]
    """
    File extension without the dot (e.g. `pdf`), taken from the platform-supplied `file_type`. Absent when the wire
    omits it.
    For an inline image, it is taken from `name` and is absent when the name has none.
    """

    scope: ConversationType
    """Conversation scope the file arrived in (the SDK's `ConversationType`)."""

    source: FileSource
    """Where the SDK found the file. Only `botActivity` is produced today."""

    attachment_style: AttachmentStyle
    """
    How the file was attached: sent as a file, or pasted inline as an image.
    See `AttachmentStyle`.
    """

    content_url: Optional[str]
    """
    Browsable URL to the file in OneDrive/SharePoint, as sent on the attachment's `content_url`.

    Not fetchable for bytes despite the name, but it is the locator a Graph `/shares` resolution keys off; bytes
    come from `download()` or `stream()`.
    For an inline image, it is the image's Bot API location instead.
    """

    raw: Any
    """
    The raw underlying attachment/graph object for escape-hatch access.
    For an inline image, only the image attachment is included; the HTML attachment that supplies its format hint
    stays in `ctx.activity.attachments`.
    """

    def __init__(
        self,
        *,
        name: str,
        scope: ConversationType,
        source: FileSource,
        unique_id: Optional[str] = None,
        content_type: Optional[str] = None,
        extension: Optional[str] = None,
        attachment_style: Optional[AttachmentStyle] = None,
        content_url: Optional[str] = None,
        raw: Any = None,
        inline_image_base_name: Optional[str] = None,
        download_url: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        credential: Optional[GraphCredential] = None,
        bot_api_credential: Optional[BotApiCredential] = None,
    ) -> None:
        self.name = name
        self.scope = scope
        self.source = source
        self.unique_id = unique_id
        self.content_type = content_type
        self.extension = extension
        self.attachment_style = attachment_style or "file"
        self.content_url = content_url
        self.raw = raw
        self._inline_image_base_name = inline_image_base_name
        self._download_url = download_url
        self._client = client
        self._credential = credential
        self._bot_api_credential = bot_api_credential
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
            filename, content_type = self._resolve_downloaded_type(data, opened.content_type)
            return DownloadedFile(
                bytes=data,
                content_type=content_type,
                filename=filename,
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

    def _resolve_downloaded_type(self, data: bytes, response_content_type: str) -> tuple[str, str]:
        """
        The filename and MIME type for downloaded bytes.

        For an inline image, recognized bytes decide, then the hint-derived name and type, because the platform can
        return a different format from the hint (a GIF downloads as a static PNG).
        """
        if self.attachment_style != "inlineImage":
            return self.name, response_content_type

        sniffed = sniff_image_format(data)

        if sniffed and self._inline_image_base_name:
            naming = inline_image_naming(self._inline_image_base_name, sniffed)
            return naming.name, naming.content_type

        return self.name, self.content_type or "application/octet-stream"

    @asynccontextmanager
    async def _open(self) -> AsyncGenerator[OpenedFileStream]:
        async with open_file_stream(
            self._target(),
            prior_fetch_succeeded=self._prior_fetch_succeeded,
            client=self._client,
            credential=self._credential,
            bot_api_credential=self._bot_api_credential,
        ) as opened:
            self._prior_fetch_succeeded = True
            yield opened

    def _target(self) -> FileFetchTarget:
        return FileFetchTarget(
            scope=self.scope,
            download_url=self._download_url,
            content_url=self.content_url,
            content_type=self.content_type,
            attachment_style=self.attachment_style,
        )
