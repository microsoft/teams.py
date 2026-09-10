"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Optional

import pytest
from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    Account,
    Attachment,
    ConversationAccount,
    MessageActivity,
)
from microsoft_teams.apps.files import FilesAccessor

CONTENT_URL = "https://contoso.sharepoint.com/personal/a/Documents/report.pdf"


def _agentic_attachment(
    *,
    name: Optional[str] = "report.pdf",
    content_url: Optional[str] = CONTENT_URL,
    content: Optional[dict] = None,
) -> Attachment:
    """
    An attachment shaped the way the platform sends one to an Agentic User: a browsable `content_url`, and no
    `download_url` anywhere in `content`.
    """
    return Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        content_url=content_url,
        name=name,
        content={"uniqueId": "odsp-unique-id", "fileType": "pdf"} if content is None else content,
    )


def _activity(attachments: list[Attachment], conversation_type: str = "personal") -> MessageActivity:
    return MessageActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type=conversation_type),
        attachments=attachments,
    )


class TestFilesAccessorWithNoDownloadUrl:
    @pytest.mark.asyncio
    async def test_surfaces_a_content_url_only_attachment_as_a_file(self):
        # An Agentic User's attachment carries a `content_url` and no `download_url`, so a mapper that requires
        # `download_url` returns an empty `list()` for every file in every scope.
        files = await FilesAccessor(_activity([_agentic_attachment()])).list()

        assert len(files) == 1
        assert files[0].name == "report.pdf"
        assert files[0].content_url == CONTENT_URL
        assert files[0].unique_id == "odsp-unique-id"
        assert files[0].extension == "pdf"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("scope", ["groupChat", "channel"])
    async def test_skips_a_content_url_only_attachment_outside_personal_scope(self, scope: str):
        # An agent in a group chat does receive these. Admitting them would put a handle in `list()` that then fails
        # at `download()`, which is worse than not surfacing it.
        files = await FilesAccessor(_activity([_agentic_attachment()], scope)).list()

        assert files == []

    @pytest.mark.asyncio
    async def test_still_surfaces_a_download_url_attachment_outside_personal_scope(self):
        # The scope condition rides on the content_url branch only, so traditional-bot behavior is unchanged: these
        # are surfaced by `list()` and raise the scope error at download time.
        attachment = _agentic_attachment(
            content={"downloadUrl": "https://download.example/r.pdf?tempauth=abc", "fileType": "pdf"}
        )

        files = await FilesAccessor(_activity([attachment], "groupChat")).list()

        assert len(files) == 1

    @pytest.mark.asyncio
    async def test_skips_an_attachment_with_neither_url(self):
        attachment = _agentic_attachment(content_url=None, content={"fileType": "pdf"})

        files = await FilesAccessor(_activity([attachment])).list()

        assert files == []

    @pytest.mark.asyncio
    async def test_skips_an_attachment_with_no_name(self):
        files = await FilesAccessor(_activity([_agentic_attachment(name=None)])).list()

        assert files == []

    @pytest.mark.asyncio
    async def test_does_not_drop_the_rest_of_the_list_when_one_entry_is_unusable(self):
        files = await FilesAccessor(
            _activity([_agentic_attachment(content_url=None, content={}), _agentic_attachment()])
        ).list()

        assert len(files) == 1
