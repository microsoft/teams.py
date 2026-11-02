"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from typing import Any, Optional, Sequence, cast

import httpx2
from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    ActivityBase,
    Attachment,
    ConversationType,
    FileDownloadInfo,
    MessageActivity,
)
from pydantic import ValidationError

from .download import BotApiCredential, GraphCredential, is_graph_route_open, is_under_service_url
from .incoming_file import IncomingFile
from .inline_image import (
    format_from_content_type,
    format_from_hint,
    inline_image_id,
    inline_image_naming,
    parse_inline_image_hints,
)
from .types import AttachmentStyle

logger = logging.getLogger(__name__)


class FilesAccessor:
    """
    Accessor for the uploaded files and inline images on the current inbound activity, exposed as `ctx.files`.

    "Files" is a filter over the raw `ctx.activity.attachments` array. Uploaded files arrive as attachments where
    `content_type` is `file.download.info`, carrying file metadata rather than the bytes themselves. The metadata
    names where the bytes live: a pre-authorized `download_url` when the platform issues one, otherwise a
    `content_url` that locates the item so Graph can resolve it. What matters is how the content arrived, not the
    file's MIME type, so any file type (pdf, docx, png, etc.) sent as an uploaded file is listed.

    Images pasted inline into the message are included, with `IncomingFile.attachment_style` set to `inlineImage`. An
    inline image not hosted on the activity's service URL is skipped with a warning. See `AttachmentStyle` for image
    formats that cannot be downloaded.

    This accessor maps each listed attachment to an `IncomingFile`, and skips everything else in `attachments`
    (adaptive cards, mentions, other non-file content) as well as malformed file entries, never throwing. For each
    file it returns, the original wire attachment (the metadata object, not the bytes) is retained on
    `IncomingFile.raw`. A malformed or non-file attachment is reachable only through the raw `activity.attachments`
    array.

    The optional `client` is the app's shared `httpx2.AsyncClient`, threaded into every `IncomingFile` so downloads
    reuse one connection pool instead of building and tearing down a client per file. It is the raw client rather
    than the SDK's wrapper on purpose: a download URL embeds its own `tempauth` credential, so the request must not
    pick up the bot's `Authorization` header. When omitted, each download creates and closes its own client.
    """

    def __init__(
        self,
        activity: ActivityBase,
        client: Optional[httpx2.AsyncClient] = None,
        credential: Optional[GraphCredential] = None,
        bot_api_credential: Optional[BotApiCredential] = None,
    ) -> None:
        self._activity = activity
        self._client = client
        self._credential = credential
        self._bot_api_credential = bot_api_credential

    async def list(self, *, attachment_style: Optional[AttachmentStyle] = None) -> list[IncomingFile]:
        """
        The files attached to the current inbound activity. Async because later scopes hydrate through Graph; the
        personal path resolves synchronously from the activity but keeps the async signature so the shape never
        breaks.

        Returns uploaded files and inline images, and makes no network requests. Filter by attachment style using the
        `attachment_style` option.
        """
        # Uploaded files only ride on inbound message activities so we validate the shape and return an empty list
        # rather than throwing.
        if not isinstance(self._activity, MessageActivity):
            return []

        attachments = self._activity.attachments or []
        scope = self._detect_scope()
        hints = self._inline_image_hints(attachments) if attachment_style != "file" else {}

        files: list[IncomingFile] = []
        for index, attachment in enumerate(attachments):
            image_id = self._inline_image_id(attachment)

            # Checked before mapping, so an attachment of the excluded style is never mapped and never logs a warning.
            if attachment_style and attachment_style != ("file" if image_id is None else "inlineImage"):
                continue

            file = (
                self._to_incoming_file(attachment, index, scope)
                if image_id is None
                else self._to_inline_image(attachment, image_id, index, scope, hints)
            )
            if file is not None:
                files.append(file)

        return files

    async def first(self, *, attachment_style: Optional[AttachmentStyle] = None) -> Optional[IncomingFile]:
        """
        Convenience: the first listed file or inline image, or `None` when none. Sugar over `list()[0]`; shares
        `list()`'s resolution so it stays correct when later scopes hydrate through Graph. Filter by attachment style
        using the `attachment_style` option.
        """
        files = await self.list(attachment_style=attachment_style)
        return files[0] if files else None

    def _detect_scope(self) -> ConversationType:
        """Derive the conversation scope from the inbound activity."""
        conversation = getattr(self._activity, "conversation", None)
        conversation_type = getattr(conversation, "conversation_type", None)
        return conversation_type or "personal"

    def _inline_image_hints(self, attachments: Sequence[Attachment]) -> dict[str, str]:
        """Format hints for inline images, keyed by attachment id, read from the message's HTML attachments."""
        hints: dict[str, str] = {}
        for attachment in attachments:
            if attachment.content_type == "text/html" and isinstance(attachment.content, str):
                hints.update(parse_inline_image_hints(attachment.content))
        return hints

    def _inline_image_id(self, attachment: Attachment) -> Optional[str]:
        """
        The inline image id when an attachment is an image pasted inline (an `image/*` attachment located at a Bot API
        inline image path), otherwise `None`.
        """
        content_type = attachment.content_type
        content_url = attachment.content_url
        if not isinstance(content_type, str) or not content_type.lower().startswith("image/"):
            return None
        if not isinstance(content_url, str):
            return None
        return inline_image_id(content_url)

    def _to_inline_image(
        self,
        attachment: Attachment,
        id: str,
        index: int,
        scope: ConversationType,
        hints: dict[str, str],
    ) -> Optional[IncomingFile]:
        """
        Map an inline image attachment to an `IncomingFile`, or `None` when its location is not on the activity's
        service URL.
        """
        content_url = cast(str, attachment.content_url)

        if not self._is_on_service_url(content_url):
            logger.warning(
                f"skipping inline image attachment at index {index}; its location is not on the activity's service URL"
            )
            return None

        hint = hints.get(id)
        format = format_from_hint(hint) if hint is not None else format_from_content_type(attachment.content_type)
        base_name = f"image-{id}"
        naming = inline_image_naming(base_name, format)

        return IncomingFile(
            name=naming.name,
            content_type=naming.content_type,
            extension=naming.extension,
            scope=scope,
            source="botActivity",
            attachment_style="inlineImage",
            content_url=content_url,
            raw=attachment,
            inline_image_base_name=base_name,
            client=self._client,
            bot_api_credential=self._bot_api_credential,
        )

    def _is_on_service_url(self, url: str) -> bool:
        """
        Whether a URL is under the activity's service URL over https.

        The download path applies the same check through `BotApiCredential.service_url`, while this one lets listing
        skip and warn.
        """
        return is_under_service_url(url, getattr(self._activity, "service_url", None))

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

        # `download_url` is fetched directly. A `content_url` without one is the agentic user case and resolves
        # through Graph, only where `is_graph_route_open` allows: the dispatcher applies the same check, so a handle
        # surfaced here cannot then fail at `download()` on scope. The `download_url` branch keeps its existing scope
        # behavior.
        # The Agentic User shape: `content` that parsed and declares no `download_url` at all. Content that failed to
        # parse, or that declares a `download_url` too malformed to use, is a broken attachment rather than an agentic
        # one. Both are excluded from the Graph route because both were skipped before it existed, and resolving one
        # would spend a Graph credential on a payload the SDK has already judged untrustworthy.
        raw_content: object = attachment.content
        declares_download_url = isinstance(raw_content, dict) and "downloadUrl" in cast("dict[str, Any]", raw_content)
        is_agentic_shape = content is not None and not declares_download_url

        actor = self._credential.actor if self._credential else None
        has_locator = bool(download_url or content_url)
        can_fetch = bool(download_url) or (is_graph_route_open(scope, actor) and is_agentic_shape and bool(content_url))

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
            attachment_style="file",
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
