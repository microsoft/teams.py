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

    @pytest.mark.asyncio
    async def test_keeps_the_preauth_route_when_a_metadata_field_is_wrong_typed(self):
        # `unique_id` and `file_type` are metadata. Rejecting the whole `content` over one of them drops the
        # `download_url` beside it, and the file then routes through Graph and fails on a bot holding no Graph
        # credential, reporting a consent problem for what is really bad data.
        # Asserted outside personal scope because the Graph route is personal-only, so a file surfaced here can only
        # have reached the list on its `download_url`.
        attachment = _agentic_attachment(
            content={"downloadUrl": "https://download.example/tempauth=abc", "uniqueId": 42, "fileType": 7}
        )

        files = await FilesAccessor(_activity([attachment], "groupChat")).list()

        assert len(files) == 1
        # Dropped one at a time rather than taken at face value, which would fail later in the sharing-url encoder.
        assert files[0].unique_id is None
        assert files[0].extension is None

    @pytest.mark.asyncio
    async def test_drops_only_the_wrong_typed_field(self):
        attachment = _agentic_attachment(
            content={
                "downloadUrl": "https://download.example/tempauth=abc",
                "uniqueId": "odsp-unique-id",
                "fileType": 7,
            }
        )

        files = await FilesAccessor(_activity([attachment], "groupChat")).list()

        assert len(files) == 1
        assert files[0].unique_id == "odsp-unique-id"
        assert files[0].extension is None

    @pytest.mark.asyncio
    async def test_does_not_open_the_graph_route_when_the_download_url_is_wrong_typed(self):
        # A declared `download_url` the SDK could not use is a broken attachment, not the agentic shape, so no route
        # applies in any scope. Falling to Graph here would resolve a payload already judged malformed, and would do
        # it on whichever identity the turn happens to carry.
        attachment = _agentic_attachment(content={"downloadUrl": 42, "uniqueId": "odsp-unique-id", "fileType": "pdf"})

        assert await FilesAccessor(_activity([attachment], "groupChat")).list() == []
        assert await FilesAccessor(_activity([attachment])).list() == []

    @pytest.mark.asyncio
    async def test_opens_the_graph_route_for_content_that_declares_no_download_url(self):
        # The agentic shape itself, which is the one case the route exists for.
        assert len(await FilesAccessor(_activity([_agentic_attachment()])).list()) == 1
