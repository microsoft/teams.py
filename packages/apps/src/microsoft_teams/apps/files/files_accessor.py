"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Any, Optional, cast

import httpx
from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    ActivityBase,
    Attachment,
    ConversationType,
    FileDownloadInfo,
    MessageActivity,
)
from pydantic import ValidationError

from .download import GraphCredential
from .incoming_file import IncomingFile

logger = logging.getLogger(__name__)


class FilesAccessor:
    """
    Accessor for the uploaded files on the current inbound activity, exposed as `ctx.files`.

    "Files" is the uploaded-file view over the raw `ctx.activity.attachments` array. Uploaded files arrive as
    attachments where `content_type` is `file.download.info`, carrying file metadata rather than the bytes themselves.
    The metadata names where the bytes live: a pre-authorized `download_url` when the platform issues one, otherwise a
    `content_url` that locates the item so Graph can resolve it. This accessor maps each to an
    `IncomingFile`, and skips everything else in `attachments` (adaptive cards, mentions, other non-file content) as
    well as malformed file entries, never throwing. For each file it returns, the original wire attachment (the
    metadata object, not the bytes) is retained on `IncomingFile.raw`. A malformed or non-file attachment is reachable
    only through the raw `activity.attachments` array.

    This covers the file-upload path, not "any uploaded media". What matters is how the content arrived, not the
    file's MIME type, so file *type* is unrestricted (pdf, docx, png, etc.) as long as it was sent as an uploaded
    file. An image sent as a file appears here, but the same image pasted inline does not.

    The optional `client` is the app's shared `httpx.AsyncClient`, threaded into every `IncomingFile` so downloads
    reuse one connection pool instead of building and tearing down a client per file. It is the raw client rather
    than the SDK's wrapper on purpose: a download URL embeds its own `tempauth` credential, so the request must not
    pick up the bot's `Authorization` header. When omitted, each download creates and closes its own client.
    """

    def __init__(
        self,
        activity: ActivityBase,
        client: Optional[httpx.AsyncClient] = None,
        credential: Optional[GraphCredential] = None,
    ) -> None:
        self._activity = activity
        self._client = client
        self._credential = credential

    async def list(self) -> list[IncomingFile]:
        """
        The files attached to the current inbound activity. Async because later scopes hydrate through Graph; the
        personal path resolves synchronously from the activity but keeps the async signature so the shape never
        breaks.

        Currently takes no arguments and returns only uploaded files. The signature is reserved to grow options later
        (e.g. `include_inline_images`, `content_types`, `include_raw`) so coverage can widen opt-in without a break;
        the default stays narrow.
        """
        # Uploaded files only ride on inbound message activities so we validate the shape and return an empty list
        # rather than throwing.
        if not isinstance(self._activity, MessageActivity):
            return []

        attachments = self._activity.attachments or []
        scope = self._detect_scope()

        files: list[IncomingFile] = []
        for index, attachment in enumerate(attachments):
            file = self._to_incoming_file(attachment, index, scope)
            if file is not None:
                files.append(file)

        return files

    async def first(self) -> Optional[IncomingFile]:
        """
        Convenience: the first attached file, or `None` when none. Sugar over `list()[0]`; shares `list()`'s
        resolution so it stays correct when later scopes hydrate through Graph.
        """
        files = await self.list()
        return files[0] if files else None

    def _detect_scope(self) -> ConversationType:
        """Derive the conversation scope from the inbound activity."""
        conversation = getattr(self._activity, "conversation", None)
        conversation_type = getattr(conversation, "conversation_type", None)
        return conversation_type or "personal"

    def _to_incoming_file(self, attachment: Attachment, index: int, scope: ConversationType) -> Optional[IncomingFile]:
        """
        Map a single activity attachment to an `IncomingFile`, or `None` when the attachment is not an uploaded file
        or is malformed. Never throws: unusable attachments are skipped so one bad entry cannot drop the rest.
        """
        # Not an uploaded file (card, mention, adaptive card, etc.). Silently ignored.
        if attachment.content_type != FILE_DOWNLOAD_INFO_CONTENT_TYPE:
            return None

        content = self._coerce_content(attachment.content, index)
        download_url = content.download_url if content else None
        content_url = attachment.content_url
        name = attachment.name

        # `download_url` is fetched directly. A `content_url` without one is the Agentic User case and resolves
        # through Graph, restricted to `personal` because agentic delivery in other scopes is unvalidated: surfacing a
        # handle there will produce a `list()` entry that then fails at `download()`. The `download_url` branch keeps
        # its existing scope behavior.
        # The Agentic User shape: `content` that parsed and declares no `download_url` at all. Content that failed to
        # parse, or that declares a `download_url` too malformed to use, is a broken attachment rather than an agentic
        # one. Both are excluded from the Graph route because both were skipped before it existed, and resolving one
        # would spend a Graph credential on a payload the SDK has already judged untrustworthy.
        raw_content: object = attachment.content
        declares_download_url = isinstance(raw_content, dict) and "downloadUrl" in cast("dict[str, Any]", raw_content)
        is_agentic_shape = content is not None and not declares_download_url

        has_locator = bool(download_url or content_url)
        can_fetch = bool(download_url) or (scope == "personal" and is_agentic_shape and bool(content_url))

        if not can_fetch or not name:
            # Split by cause: a malformed attachment is a real defect, while an out-of-scope file is expected noise.
            if not name or not has_locator:
                missing = "name" if not name else "a download or content URL"
                logger.warning(f"skipping file.download.info attachment at index {index}; missing {missing}")
            else:
                logger.debug(
                    f"skipping file.download.info attachment at index {index}; "
                    f"'{scope}' scope files are not fetchable yet"
                )
            return None

        return IncomingFile(
            name=name,
            scope=scope,
            source="botActivity",
            unique_id=content.unique_id if content else None,
            # `file_type` is the platform-supplied extension (e.g. `pdf`); left `None` when the wire omits it,
            # matching how peer SDKs surface it.
            extension=content.file_type if content else None,
            # Browsable link to the file in OneDrive/SharePoint. Not directly fetchable like `download_url`, but it
            # is the locator a Graph `/shares` resolution keys off.
            content_url=content_url,
            raw=attachment,
            download_url=download_url,
            client=self._client,
            credential=self._credential,
        )

    def _coerce_content(self, content: object, index: int) -> Optional[FileDownloadInfo]:
        """Normalize the attachment's raw `content` (a wire dict or an already-parsed model) to `FileDownloadInfo`."""
        if isinstance(content, FileDownloadInfo):
            return content
        if isinstance(content, dict):
            # Wrong-typed fields are dropped one at a time rather than rejecting the whole object. `unique_id` and
            # `file_type` are metadata, so failing on one of them would drop a usable `download_url` and route a
            # traditional bot's file through Graph, which then fails reporting a consent problem that was never the
            # cause.
            narrowed = {
                key: value
                for key, value in cast("dict[str, Any]", content).items()
                if value is None or isinstance(value, str)
            }
            try:
                return FileDownloadInfo.model_validate(narrowed)
            except ValidationError:
                logger.debug(f"skipping file.download.info attachment at index {index}; content failed validation")
                return None
        return None
