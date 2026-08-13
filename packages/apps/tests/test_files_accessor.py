"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import List, Optional

import httpx
import pytest
from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    Account,
    Attachment,
    ConversationAccount,
    MessageActivity,
)
from microsoft_teams.api.activities.typing import TypingActivity
from microsoft_teams.apps.files import FilesAccessor, download


def _activity_with(attachments: List[Attachment], conversation_type: Optional[str] = "personal") -> MessageActivity:
    return MessageActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type=conversation_type),
        attachments=attachments,
    )


async def test_maps_a_file_download_info_attachment_to_an_incoming_file() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        content_url="https://contoso.sharepoint.com/report.pdf",
        name="report.pdf",
        content={
            "downloadUrl": "https://download.example/report.pdf?tempauth=abc",
            "uniqueId": "odsp-unique-id",
            "fileType": "pdf",
        },
    )

    files = await FilesAccessor(_activity_with([attachment])).list()

    assert len(files) == 1
    file = files[0]
    assert file.unique_id == "odsp-unique-id"
    assert file.name == "report.pdf"
    assert file.extension == "pdf"
    assert file.scope == "personal"
    assert file.source == "botActivity"
    assert file.web_url == "https://contoso.sharepoint.com/report.pdf"
    assert file.raw is attachment


async def test_ignores_attachments_that_are_not_uploaded_files() -> None:
    card = Attachment(content_type="application/vnd.microsoft.card.adaptive", content={})

    files = await FilesAccessor(_activity_with([card])).list()

    assert files == []


async def test_skips_a_malformed_file_download_info_missing_download_url() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="broken.pdf",
        content={"uniqueId": "no-url"},
    )

    files = await FilesAccessor(_activity_with([attachment])).list()

    assert files == []


async def test_skips_a_file_download_info_whose_content_fails_validation() -> None:
    # `content` is a dict but the wire shape is wrong (downloadUrl is not a string), so
    # `FileDownloadInfo.model_validate` would raise. The accessor must skip it, not throw.
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="broken.pdf",
        content={"downloadUrl": {"not": "a string"}},
    )

    files = await FilesAccessor(_activity_with([attachment])).list()

    assert files == []


async def test_skips_a_file_download_info_missing_a_name() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        content={"downloadUrl": "https://download.example/anon"},
    )

    files = await FilesAccessor(_activity_with([attachment])).list()

    assert files == []


async def test_maps_a_file_that_has_no_unique_id() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="anon.pdf",
        content={"downloadUrl": "https://download.example/anon.pdf"},
    )

    files = await FilesAccessor(_activity_with([attachment])).list()

    file = files[0]
    assert file.name == "anon.pdf"
    assert file.unique_id is None


async def test_defaults_the_scope_to_personal_when_conversation_type_is_absent() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="a.pdf",
        content={"downloadUrl": "https://download.example/a.pdf", "uniqueId": "a"},
    )

    files = await FilesAccessor(_activity_with([attachment], conversation_type=None)).list()

    assert files[0].scope == "personal"


async def test_returns_empty_list_when_the_activity_has_no_attachments() -> None:
    files = await FilesAccessor(_activity_with([])).list()

    assert files == []


async def test_returns_empty_list_when_the_attachments_field_is_absent() -> None:
    activity = MessageActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="personal"),
    )

    files = await FilesAccessor(activity).list()

    assert files == []


async def test_returns_empty_list_for_non_message_activities() -> None:
    typing = TypingActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="personal"),
    )

    files = await FilesAccessor(typing).list()

    assert files == []


async def test_first_returns_the_first_mapped_file_or_none() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="a.pdf",
        content={"downloadUrl": "https://download.example/a.pdf", "uniqueId": "a"},
    )

    assert await FilesAccessor(_activity_with([attachment])).first() is not None
    assert await FilesAccessor(_activity_with([])).first() is None


async def test_threads_the_shared_client_into_every_mapped_file() -> None:
    """The injected client must reach the download path; otherwise each download builds its own connection pool."""
    calls: List[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(200, content=b"shared", headers={"content-type": "text/plain"})

    shared = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="notes.txt",
        content={"downloadUrl": "https://download.example/notes.txt?tempauth=abc"},
    )

    try:
        files = await FilesAccessor(_activity_with([attachment]), shared).list()
        downloaded = await files[0].download()
    finally:
        await shared.aclose()

    # A file that fell back to its own client would never hit this transport.
    assert calls == ["https://download.example/notes.txt?tempauth=abc"]
    assert downloaded.text() == "shared"


async def test_falls_back_to_a_private_client_when_none_is_injected() -> None:
    """Omitting the client must still download, through a private client the download path creates and then closes."""
    created: List[httpx.AsyncClient] = []
    real_client_cls = httpx.AsyncClient

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"private", headers={"content-type": "text/plain"})

    def fake_client_cls(*_args: object, **_kwargs: object) -> httpx.AsyncClient:
        client = real_client_cls(transport=httpx.MockTransport(handler))
        created.append(client)
        return client

    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="notes.txt",
        content={"downloadUrl": "https://download.example/notes.txt"},
    )

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(download.httpx, "AsyncClient", fake_client_cls)
        files = await FilesAccessor(_activity_with([attachment])).list()
        downloaded = await files[0].download()

    assert len(files) == 1
    assert downloaded.text() == "private"
    # The download path owns the client it created, so it must also close it rather than leak the pool.
    assert len(created) == 1
    assert created[0].is_closed
