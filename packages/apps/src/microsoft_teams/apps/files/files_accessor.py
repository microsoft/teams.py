"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import List, Optional

from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    ActivityBase,
    Attachment,
    ConversationType,
    FileDownloadInfo,
    MessageActivity,
)
from pydantic import ValidationError

from .incoming_file import IncomingFile

logger = logging.getLogger(__name__)


class FilesAccessor:
    """
    Accessor for the uploaded files on the current inbound activity, exposed as `ctx.files`.

    "Files" is the uploaded-file view over the raw `ctx.activity.attachments` array. Uploaded files arrive as
    attachments where `content_type` is `file.download.info`, carrying file metadata (a `download_url` plus
    identifiers) rather than the bytes themselves, which are fetched from that URL. This accessor maps each to an
    `IncomingFile`, and skips everything else in `attachments` (adaptive cards, mentions, other non-file content) as
    well as malformed file entries, never throwing. For each file it returns, the original wire attachment (the
    metadata object, not the bytes) is retained on `IncomingFile.raw`. A malformed or non-file attachment is reachable
    only through the raw `activity.attachments` array.

    This covers the file-upload path, not "any uploaded media". What matters is how the content arrived, not the
    file's MIME type, so file *type* is unrestricted (pdf, docx, png, etc.) as long as it was sent as an uploaded
    file. An image sent as a file appears here, but the same image pasted inline does not.
    """

    def __init__(self, activity: ActivityBase) -> None:
        self._activity = activity

    async def list(self) -> List[IncomingFile]:
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

        files: List[IncomingFile] = []
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
        name = attachment.name

        # A `file.download.info` without fetchable URL or name cannot be turned into a usable handle. Skip it and
        # leave a breadcrumb rather than throwing.
        if not download_url or not name:
            missing = "name" if not name else "download_url"
            logger.debug(f"files: skipping file.download.info attachment at index {index}; missing {missing}")
            return None

        return IncomingFile(
            name=name,
            scope=scope,
            source="botActivity",
            unique_id=content.unique_id if content else None,
            # `file_type` is the platform-supplied extension (e.g. `pdf`); left `None` when the wire omits it,
            # matching how peer SDKs surface it.
            extension=content.file_type if content else None,
            # Maps the wire's `content_url` (a browsable link to the file in OneDrive/SharePoint) to `web_url`; not
            # fetchable like `download_url`.
            web_url=attachment.content_url,
            raw=attachment,
            download_url=download_url,
        )

    def _coerce_content(self, content: object, index: int) -> Optional[FileDownloadInfo]:
        """Normalize the attachment's raw `content` (a wire dict or an already-parsed model) to `FileDownloadInfo`."""
        if isinstance(content, FileDownloadInfo):
            return content
        if isinstance(content, dict):
            try:
                return FileDownloadInfo.model_validate(content)
            except ValidationError:
                logger.debug(
                    f"files: skipping file.download.info attachment at index {index}; content failed validation"
                )
                return None
        return None
