"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import json
from typing import List, Optional

import httpx
import pytest
from microsoft_teams.api import ConversationType
from microsoft_teams.apps.files.download import (
    BotApiCredential,
    FileFetchTarget,
    is_under_service_url,
    open_file_stream,
)
from microsoft_teams.apps.files.errors import (
    FileError,
    InlineImageAccessError,
    InlineImageTransformationError,
)
from microsoft_teams.apps.files.incoming_file import IncomingFile

SERVICE_URL = "https://smba.trafficmanager.net/amer/"
CONTENT_URL = f"{SERVICE_URL}v3/attachments/a1/views/original"

PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 0])
GIF = bytes([0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0, 0])
JPEG = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0, 0])
WEBP = bytes([0x52, 0x49, 0x46, 0x46, 0, 0, 0, 0, 0x57, 0x45, 0x42, 0x50])
UNKNOWN = bytes([0x42, 0x4D, 0, 0, 0, 0])


class _Recorder:
    """Records every request the dispatcher makes, so a route's request count is observable rather than inferred."""

    def __init__(self, status: int = 200, body: Optional[bytes] = None, content_type: Optional[str] = None) -> None:
        self._status = status
        self._body = body
        self._content_type = content_type
        self.calls: List[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        headers = {"content-type": self._content_type} if self._content_type else {}
        return httpx.Response(self._status, content=self._body or b"", headers=headers)

    @property
    def client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=httpx.MockTransport(self.handler))

    def auth_of(self, index: int) -> Optional[str]:
        return self.calls[index].headers.get("Authorization")


class _CountingToken:
    """A token source that reports whether it was ever resolved, so a refusal can be proven to precede it."""

    def __init__(self, value: Optional[str] = "bot-api-token") -> None:
        self._value = value
        self.calls = 0

    async def __call__(self) -> Optional[str]:
        self.calls += 1
        return self._value


def _credential(
    *,
    actor: str = "app",
    token: Optional[object] = None,
    service_url: Optional[str] = SERVICE_URL,
) -> BotApiCredential:
    return BotApiCredential(actor=actor, token=token or _CountingToken(), service_url=service_url)


def _inline_file(
    recorder: _Recorder,
    *,
    name: str = "image-a1.gif",
    content_type: Optional[str] = "image/gif",
    scope: ConversationType = "groupChat",
    credential: Optional[BotApiCredential] = None,
    content_url: str = CONTENT_URL,
) -> IncomingFile:
    return IncomingFile(
        name=name,
        content_type=content_type,
        extension="gif",
        scope=scope,
        source="botActivity",
        attachment_style="inlineImage",
        content_url=content_url,
        inline_image_base_name="image-a1",
        bot_api_credential=credential or _credential(),
        client=recorder.client,
    )


@pytest.mark.asyncio
async def test_reads_the_content_url_with_the_bot_api_token_in_a_scope_the_file_routes_do_not_open():
    recorder = _Recorder(body=PNG)

    await _inline_file(recorder, scope="channel").download()

    assert [str(call.url) for call in recorder.calls] == [CONTENT_URL]
    assert recorder.auth_of(0) == "Bearer bot-api-token"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data, filename, content_type",
    [
        (PNG, "image-a1.png", "image/png"),
        (JPEG, "image-a1.jpg", "image/jpeg"),
        (GIF, "image-a1.gif", "image/gif"),
        (WEBP, "image-a1.webp", "image/webp"),
    ],
    ids=["PNG", "JPEG", "GIF", "WebP"],
)
async def test_names_and_types_bytes_from_the_bytes_over_the_hint_and_the_response_header(
    data: bytes, filename: str, content_type: str
):
    recorder = _Recorder(body=data, content_type="application/octet-stream")

    downloaded = await _inline_file(recorder, name="image-a1.gif", content_type="image/gif").download()

    assert downloaded.filename == filename
    assert downloaded.content_type == content_type


@pytest.mark.asyncio
async def test_falls_back_to_the_hint_derived_name_and_type_when_the_bytes_are_not_recognized():
    recorder = _Recorder(body=UNKNOWN, content_type="image/png")

    downloaded = await _inline_file(recorder, name="image-a1.gif", content_type="image/gif").download()

    assert downloaded.filename == "image-a1.gif"
    assert downloaded.content_type == "image/gif"


@pytest.mark.asyncio
async def test_falls_back_to_no_extension_and_octet_stream_when_neither_the_bytes_nor_the_hint_name_a_format():
    recorder = _Recorder(body=UNKNOWN, content_type="image/bmp")

    downloaded = await _inline_file(recorder, name="image-a1", content_type="application/octet-stream").download()

    assert downloaded.filename == "image-a1"
    assert downloaded.content_type == "application/octet-stream"


@pytest.mark.asyncio
async def test_leaves_the_handle_unchanged_when_the_bytes_disagree_with_the_hint():
    recorder = _Recorder(body=PNG)
    file = _inline_file(recorder, name="image-a1.gif", content_type="image/gif")

    await file.download()

    assert file.name == "image-a1.gif"
    assert file.content_type == "image/gif"
    assert file.extension == "gif"


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [None, "   "], ids=["missing", "blank"])
async def test_throws_before_any_request_when_no_bot_api_token_is_available(value: Optional[str]):
    recorder = _Recorder(body=PNG)
    token = _CountingToken(value)

    with pytest.raises(RuntimeError, match="no Bot API token is available"):
        await _inline_file(recorder, credential=_credential(token=token)).download()

    assert token.calls == 1
    assert recorder.calls == []


@pytest.mark.asyncio
async def test_refuses_a_content_url_that_is_not_https():
    recorder = _Recorder(body=PNG)

    with pytest.raises(RuntimeError, match="must use https"):
        async with open_file_stream(
            FileFetchTarget(
                scope="personal",
                attachment_style="inlineImage",
                content_url="http://smba.trafficmanager.net/amer/v3/attachments/a1/views/original",
            ),
            client=recorder.client,
            bot_api_credential=_credential(),
        ):
            pass

    assert recorder.calls == []


@pytest.mark.parametrize(
    "url, service_url",
    [
        (f"{SERVICE_URL}v3/attachments/a1/views/original", SERVICE_URL),
        (f"{SERVICE_URL}v3/x", "https://smba.trafficmanager.net/amer"),
        ("https://SMBA.trafficmanager.net/amer/v3/x", SERVICE_URL),
        ("https://smba.trafficmanager.net/v3/x", "https://smba.trafficmanager.net"),
        (f"{SERVICE_URL}%2e/v3/x", SERVICE_URL),
        ("https://smba.trafficmanager.net/%2e/amer/v3/x", SERVICE_URL),
        (f"{SERVICE_URL}..%2f..%2f/v3/x", SERVICE_URL),
    ],
    ids=[
        "the service URL path",
        "a service URL without a trailing slash",
        "a host that differs only in case",
        "a service URL with no path",
        "a percent-encoded single dot segment",
        "a percent-encoded single dot segment ahead of the service URL path",
        "an encoded slash, which is not a separator",
    ],
)
def test_is_under_service_url_accepts(url: str, service_url: str):
    assert is_under_service_url(url, service_url) is True


@pytest.mark.parametrize(
    "url, service_url",
    [
        ("https://smba.trafficmanager.net/americas/v3/x", "https://smba.trafficmanager.net/amer"),
        (f"{SERVICE_URL}../v3/x", SERVICE_URL),
        (f"{SERVICE_URL}%2e%2e/v3/x", SERVICE_URL),
        (f"{SERVICE_URL}%2E%2e/v3/x", SERVICE_URL),
        (f"{SERVICE_URL}.%2e/v3/x", SERVICE_URL),
        ("https://attacker.example/amer/v3/x", SERVICE_URL),
        ("https://smba.trafficmanager.net.attacker.example/amer/v3/x", "https://smba.trafficmanager.net"),
        ("https://smba.trafficmanager.net:8443/amer/v3/x", SERVICE_URL),
        ("http://smba.trafficmanager.net/amer/v3/x", SERVICE_URL),
        ("http://smba.trafficmanager.net/amer/v3/x", "http://smba.trafficmanager.net/amer/"),
        (f"{SERVICE_URL}v3/x", None),
        (f"{SERVICE_URL}v3/x", "not a url"),
        ("not a url", SERVICE_URL),
    ],
    ids=[
        "a sibling path that shares a prefix",
        "a dot segment that climbs out",
        "a percent-encoded dot segment that climbs out",
        "a percent-encoded dot segment in mixed case",
        "a half-encoded dot segment that climbs out",
        "another host",
        "a lookalike host",
        "another port",
        "an http target",
        "an http service URL",
        "a missing service URL",
        "an unparseable service URL",
        "an unparseable target",
    ],
)
def test_is_under_service_url_rejects(url: str, service_url: Optional[str]):
    assert is_under_service_url(url, service_url) is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_url",
    [
        "https://attacker.example/amer/v3/attachments/a1/views/original",
        f"{SERVICE_URL}../v3/attachments/a1/views/original",
    ],
    ids=["another host", "a dot segment that climbs out of the service URL path"],
)
async def test_refuses_a_forged_target_before_resolving_the_token_or_sending_a_request(content_url: str):
    recorder = _Recorder(body=PNG)
    token = _CountingToken()

    with pytest.raises(RuntimeError, match="content URL is not under the activity's service URL"):
        await _inline_file(recorder, content_url=content_url, credential=_credential(token=token)).download()

    assert token.calls == 0
    assert recorder.calls == []


@pytest.mark.asyncio
async def test_refuses_every_inline_image_when_the_credential_carries_no_service_url():
    recorder = _Recorder(body=PNG)
    token = _CountingToken()

    with pytest.raises(RuntimeError, match="not under the activity's service URL"):
        await _inline_file(recorder, credential=_credential(token=token, service_url=None)).download()

    assert token.calls == 0
    assert recorder.calls == []


@pytest.mark.asyncio
async def test_resolves_a_plain_string_token_source():
    recorder = _Recorder(body=PNG)

    await _inline_file(recorder, credential=_credential(token="bot-api-token")).download()

    assert recorder.auth_of(0) == "Bearer bot-api-token"


TRANSFORMATION_BODY = json.dumps(
    {"error": {"code": "TransformationFailed", "message": "Failed to transform the image"}}
).encode()


@pytest.mark.asyncio
async def test_maps_415_to_inline_image_transformation_error_with_the_status_code_and_service_text():
    recorder = _Recorder(status=415, body=TRANSFORMATION_BODY)

    with pytest.raises(InlineImageTransformationError) as caught:
        await _inline_file(recorder).download()

    error = caught.value
    assert isinstance(error, FileError)
    assert error.status == 415
    assert error.code == "TransformationFailed"
    assert error.details == "TransformationFailed: Failed to transform the image"
    assert error.actor == "app"
    assert str(error) == (
        "cannot download inline image: the platform could not convert it for download "
        "(status 415, code TransformationFailed). Some image formats, such as BMP and AVIF, cannot be converted by "
        "the platform, so Teams shows a placeholder, and they cannot be downloaded. Ask the user to send the image "
        "as a file attachment instead (service said: TransformationFailed: Failed to transform the image)"
    )


@pytest.mark.asyncio
async def test_omits_the_code_segment_and_keeps_the_raw_text_when_a_415_body_is_not_json():
    recorder = _Recorder(status=415, body=b"<html>unsupported</html>")

    with pytest.raises(InlineImageTransformationError) as caught:
        await _inline_file(recorder).download()

    error = caught.value
    assert error.code is None
    assert error.details == "<html>unsupported</html>"
    assert "(status 415). Some image formats" in str(error)
    assert "(service said: <html>unsupported</html>)" in str(error)


@pytest.mark.asyncio
async def test_omits_the_service_said_suffix_when_a_415_has_no_body():
    recorder = _Recorder(status=415)

    with pytest.raises(InlineImageTransformationError) as caught:
        await _inline_file(recorder).download()

    error = caught.value
    assert error.details is None
    assert str(error).endswith("send the image as a file attachment instead")


@pytest.mark.asyncio
async def test_truncates_a_long_service_message():
    recorder = _Recorder(status=415, body=b"x" * 10_000)

    with pytest.raises(InlineImageTransformationError) as caught:
        await _inline_file(recorder).download()

    assert caught.value.details == "x" * 2048


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403])
async def test_maps_a_refusal_to_inline_image_access_error_naming_the_identity(status: int):
    recorder = _Recorder(
        status=status, body=json.dumps({"error": {"code": "Unauthorized", "message": "nope"}}).encode()
    )
    agentic = _credential(actor="agentic_user", token="agent-token")

    with pytest.raises(InlineImageAccessError) as caught:
        await _inline_file(recorder, credential=agentic).download()

    error = caught.value
    assert isinstance(error, FileError)
    assert error.status == status
    assert error.actor == "agentic_user"
    assert error.details == "Unauthorized: nope"
    assert str(error) == (
        "cannot download inline image: the Bot API token presented for the agentic user was rejected with status "
        f"{status} (service said: Unauthorized: nope)"
    )


@pytest.mark.asyncio
async def test_surfaces_another_failure_status_as_a_plain_error_carrying_the_service_text():
    recorder = _Recorder(status=500, body=json.dumps({"error": {"code": "ServerError", "message": "boom"}}).encode())

    with pytest.raises(RuntimeError) as caught:
        await _inline_file(recorder).download()

    error = caught.value
    assert not isinstance(error, FileError)
    assert "500" in str(error)
    assert "ServerError: boom" in str(error)
