"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import logging
from typing import List, Optional

import pytest
from microsoft_teams.api import (
    FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    Account,
    Attachment,
    ConversationAccount,
    MessageActivity,
)
from microsoft_teams.apps.files import FilesAccessor

SERVICE_URL = "https://smba.trafficmanager.net/amer/"


def _inline_image(id: str, content_type: str = "image/*", service_url: str = SERVICE_URL) -> Attachment:
    return Attachment(content_type=content_type, content_url=f"{service_url}v3/attachments/{id}/views/original")


def _html(*images: tuple[str, Optional[str]]) -> Attachment:
    tags = ""
    for id, scope in images:
        itemscope = "" if scope is None else f' itemscope="{scope}"'
        tags += (
            f'<img src="{SERVICE_URL}v3/attachments/{id}/views/original" '
            f'itemtype="http://schema.skype.com/AMSImage"{itemscope} itemid="{id}" width="250">'
        )
    return Attachment(content_type="text/html", content=f"<p>look</p><p>{tags}</p>")


def _activity_with(attachments: List[Attachment], service_url: Optional[str] = SERVICE_URL) -> MessageActivity:
    activity = MessageActivity(
        id="activity-id",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="groupChat"),
        attachments=attachments,
    )
    activity.service_url = service_url
    return activity


REPORT_PDF = Attachment(
    content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
    content_url="https://contoso.sharepoint.com/report.pdf",
    name="report.pdf",
    content={"downloadUrl": "https://download.example/report.pdf?tempauth=abc", "fileType": "pdf"},
)


def _mixed() -> MessageActivity:
    return _activity_with([_inline_image("a1"), REPORT_PDF, _inline_image("b2"), _html(("a1", "png"), ("b2", "png"))])


@pytest.mark.parametrize(
    "hint, name, extension, content_type",
    [
        ("png", "image-a1.png", "png", "image/png"),
        ("jpeg", "image-a1.jpg", "jpg", "image/jpeg"),
        ("gif", "image-a1.gif", "gif", "image/gif"),
        ("webp", "image-a1.webp", "webp", "image/webp"),
    ],
)
async def test_names_and_types_a_hint(hint: str, name: str, extension: str, content_type: str) -> None:
    image = _inline_image("a1")

    files = await FilesAccessor(_activity_with([image, _html((("a1"), hint))])).list()

    assert len(files) == 1
    file = files[0]
    assert file.name == name
    assert file.extension == extension
    assert file.content_type == content_type
    assert file.attachment_style == "inlineImage"
    assert file.source == "botActivity"
    assert file.scope == "groupChat"
    assert file.content_url == image.content_url
    assert file.raw is image
    assert file.unique_id is None


@pytest.mark.parametrize("hint", ["bmp", "avif", ""])
async def test_gives_an_unconvertible_hint_no_extension_and_octet_stream(hint: str) -> None:
    files = await FilesAccessor(_activity_with([_inline_image("a1"), _html(("a1", hint))])).list()

    assert files[0].name == "image-a1"
    assert files[0].extension is None
    assert files[0].content_type == "application/octet-stream"


async def test_gives_a_missing_hint_no_extension_and_octet_stream_rather_than_assuming_png() -> None:
    files = await FilesAccessor(_activity_with([_inline_image("a1"), _html(("a1", None))])).list()

    assert files[0].name == "image-a1"
    assert files[0].content_type == "application/octet-stream"


async def test_falls_back_to_the_attachment_content_type_only_when_no_hint_is_present() -> None:
    without_html = await FilesAccessor(_activity_with([_inline_image("a1", "image/jpeg")])).list()
    wildcard = await FilesAccessor(_activity_with([_inline_image("a1", "image/*")])).list()
    hint_wins = await FilesAccessor(_activity_with([_inline_image("a1", "image/jpeg"), _html(("a1", "bmp"))])).list()

    assert (without_html[0].name, without_html[0].content_type) == ("image-a1.jpg", "image/jpeg")
    assert (wildcard[0].name, wildcard[0].content_type) == ("image-a1", "application/octet-stream")
    assert (hint_wins[0].name, hint_wins[0].content_type) == ("image-a1", "application/octet-stream")


async def test_lists_several_inline_images_alongside_a_file_attachment_each_with_its_own_style() -> None:
    file = Attachment(
        content_type=FILE_DOWNLOAD_INFO_CONTENT_TYPE,
        content_url="https://contoso.sharepoint.com/report.pdf",
        name="report.pdf",
        content={
            "downloadUrl": "https://download.example/report.pdf?tempauth=abc",
            "fileType": "pdf",
            "uniqueId": "u1",
        },
    )
    activity = _activity_with([_inline_image("a1"), file, _inline_image("b2"), _html(("a1", "png"), ("b2", "webp"))])

    files = await FilesAccessor(activity).list()

    assert [(f.name, f.attachment_style) for f in files] == [
        ("image-a1.png", "inlineImage"),
        ("report.pdf", "file"),
        ("image-b2.webp", "inlineImage"),
    ]
    assert files[1].unique_id == "u1"


async def test_returns_both_styles_when_the_attachment_style_option_is_omitted() -> None:
    files = await FilesAccessor(_mixed()).list()

    assert [f.name for f in files] == ["image-a1.png", "report.pdf", "image-b2.png"]


async def test_returns_only_file_attachments_for_file() -> None:
    files = await FilesAccessor(_mixed()).list(attachment_style="file")

    assert [f.name for f in files] == ["report.pdf"]


async def test_returns_only_pasted_images_for_inline_image() -> None:
    files = await FilesAccessor(_mixed()).list(attachment_style="inlineImage")

    assert [f.name for f in files] == ["image-a1.png", "image-b2.png"]


async def test_lets_first_skip_a_leading_pasted_image() -> None:
    accessor = FilesAccessor(_mixed())

    first = await accessor.first()
    first_file = await accessor.first(attachment_style="file")

    assert first is not None and first.name == "image-a1.png"
    assert first_file is not None and first_file.name == "report.pdf"


async def test_lets_first_return_none_when_no_file_has_the_style() -> None:
    accessor = FilesAccessor(_activity_with([_inline_image("a1")]))

    assert await accessor.first(attachment_style="file") is None


async def test_does_not_warn_about_an_inline_image_it_was_never_going_to_return(
    caplog: pytest.LogCaptureFixture,
) -> None:
    elsewhere = _inline_image("a1", "image/*", "https://attacker.example/amer/")

    with caplog.at_level(logging.WARNING):
        files = await FilesAccessor(_activity_with([elsewhere, REPORT_PDF])).list(attachment_style="file")

    assert [f.name for f in files] == ["report.pdf"]
    assert caplog.records == []


async def test_reads_hints_regardless_of_attribute_order_or_quote_style() -> None:
    reordered = Attachment(
        content_type="text/html",
        content="<img itemid='a1' itemscope='gif' alt=\"x\" itemtype='http://schema.skype.com/AMSImage'>",
    )

    files = await FilesAccessor(_activity_with([_inline_image("a1"), reordered])).list()

    assert files[0].name == "image-a1.gif"


async def test_ignores_an_img_hint_that_is_not_marked_as_an_inline_image() -> None:
    other = Attachment(content_type="text/html", content='<img itemid="a1" itemscope="png" itemtype="other">')

    files = await FilesAccessor(_activity_with([_inline_image("a1"), other])).list()

    assert files[0].name == "image-a1"


async def test_skips_an_inline_image_that_is_not_on_the_activity_service_url_with_a_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    elsewhere = _inline_image("a1", "image/*", "https://attacker.example/amer/")

    with caplog.at_level(logging.WARNING):
        files = await FilesAccessor(_activity_with([elsewhere, _inline_image("b2")])).list()

    assert [f.name for f in files] == ["image-b2"]
    assert "skipping inline image attachment at index 0; its location is not on the activity's service URL" in (
        caplog.text
    )


async def test_does_not_let_a_lookalike_host_match_a_service_url_that_lacks_a_trailing_slash(
    caplog: pytest.LogCaptureFixture,
) -> None:
    lookalike = _inline_image("a1", "image/*", "https://smba.trafficmanager.net.attacker.example/")

    with caplog.at_level(logging.WARNING):
        files = await FilesAccessor(_activity_with([lookalike], "https://smba.trafficmanager.net")).list()

    assert files == []
    assert "not on the activity's service URL" in caplog.text


async def test_does_not_let_a_dot_segment_climb_out_of_the_service_url_path(
    caplog: pytest.LogCaptureFixture,
) -> None:
    climbing = _inline_image("a1", "image/*", "https://smba.trafficmanager.net/amer/TENANT/../../")

    with caplog.at_level(logging.WARNING):
        files = await FilesAccessor(_activity_with([climbing], "https://smba.trafficmanager.net/amer/TENANT/")).list()

    assert files == []
    assert "not on the activity's service URL" in caplog.text


async def test_matches_a_service_url_without_a_trailing_slash() -> None:
    files = await FilesAccessor(
        _activity_with(
            [_inline_image("a1", "image/*", "https://smba.trafficmanager.net/amer/")],
            "https://smba.trafficmanager.net/amer",
        )
    ).list()

    assert len(files) == 1


async def test_matches_a_service_url_whose_host_differs_only_in_case_keeping_the_content_url_as_sent() -> None:
    image = _inline_image("a1", "image/*", "https://SMBA.TrafficManager.net/amer/")

    files = await FilesAccessor(_activity_with([image], "https://smba.trafficmanager.net/amer/")).list()

    assert len(files) == 1
    assert files[0].content_url == image.content_url


async def test_skips_inline_images_when_the_activity_has_no_service_url(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        files = await FilesAccessor(_activity_with([_inline_image("a1")], None)).list()

    assert files == []
    assert "not on the activity's service URL" in caplog.text


async def test_leaves_an_image_attachment_that_is_not_at_an_inline_image_location_alone() -> None:
    attachment = Attachment(content_type="image/png", content_url=f"{SERVICE_URL}v3/somewhere/else.png")

    files = await FilesAccessor(_activity_with([attachment])).list()

    assert files == []
