"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import logging
from typing import List, Optional

from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    Account,
    Attachment,
    ConversationAccount,
    MessageActivity,
)
from microsoft_teams.api.activities.typing import TypingActivity
from microsoft_teams.apps.files import FilesAccessor

log = logging.getLogger("test_files_accessor")


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

    files = await FilesAccessor(_activity_with([attachment]), log).list()

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

    files = await FilesAccessor(_activity_with([card]), log).list()

    assert files == []


async def test_skips_a_malformed_file_download_info_missing_download_url() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="broken.pdf",
        content={"uniqueId": "no-url"},
    )

    files = await FilesAccessor(_activity_with([attachment]), log).list()

    assert files == []


async def test_skips_a_file_download_info_missing_a_name() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        content={"downloadUrl": "https://download.example/anon"},
    )

    files = await FilesAccessor(_activity_with([attachment]), log).list()

    assert files == []


async def test_maps_a_file_that_has_no_unique_id() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="anon.pdf",
        content={"downloadUrl": "https://download.example/anon.pdf"},
    )

    files = await FilesAccessor(_activity_with([attachment]), log).list()

    file = files[0]
    assert file.name == "anon.pdf"
    assert file.unique_id is None


async def test_defaults_the_scope_to_personal_when_conversation_type_is_absent() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="a.pdf",
        content={"downloadUrl": "https://download.example/a.pdf", "uniqueId": "a"},
    )

    files = await FilesAccessor(_activity_with([attachment], conversation_type=None), log).list()

    assert files[0].scope == "personal"


async def test_returns_empty_list_when_the_activity_has_no_attachments() -> None:
    files = await FilesAccessor(_activity_with([]), log).list()

    assert files == []


async def test_returns_empty_list_when_the_attachments_field_is_absent() -> None:
    activity = MessageActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="personal"),
    )

    files = await FilesAccessor(activity, log).list()

    assert files == []


async def test_returns_empty_list_for_non_message_activities() -> None:
    typing = TypingActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="personal"),
    )

    files = await FilesAccessor(typing, log).list()

    assert files == []


async def test_first_returns_the_first_mapped_file_or_none() -> None:
    attachment = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        name="a.pdf",
        content={"downloadUrl": "https://download.example/a.pdf", "uniqueId": "a"},
    )

    assert await FilesAccessor(_activity_with([attachment]), log).first() is not None
    assert await FilesAccessor(_activity_with([]), log).first() is None
