"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

import httpx
import pytest
from microsoft_teams.apps.files import IncomingFile
from microsoft_teams.apps.files.errors import FileScopeNotSupportedError, FileUrlExpiredError

DOWNLOAD_URL = "https://download.example/notes.txt?tempauth=abc"


def _json_body(text: str, headers: Optional[Dict[str, str]] = None) -> httpx.Response:
    return httpx.Response(200, content=text.encode(), headers=headers or {})


def _sequence_client(responses: List[httpx.Response]) -> Tuple[httpx.AsyncClient, List[str]]:
    """A client whose transport hands back the given responses in call order, recording the urls it saw."""
    calls: List[str] = []
    state = {"i": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        index = min(state["i"], len(responses) - 1)
        state["i"] += 1
        return responses[index]

    return httpx.AsyncClient(transport=httpx.MockTransport(handler)), calls


@asynccontextmanager
async def _personal_file(responses: List[httpx.Response], **init: Any) -> AsyncIterator[Tuple[IncomingFile, List[str]]]:
    client, calls = _sequence_client(responses)
    params: Dict[str, Any] = {
        "name": "notes.txt",
        "scope": "personal",
        "source": "botActivity",
        "download_url": DOWNLOAD_URL,
    }
    params.update(init)
    try:
        yield IncomingFile(client=client, **params), calls
    finally:
        await client.aclose()


class TestDownload:
    async def test_fetches_the_download_url_and_buffers_the_bytes(self) -> None:
        async with _personal_file([_json_body("hello world", {"content-type": "text/plain"})]) as (file, calls):
            downloaded = await file.download()

            assert calls == [DOWNLOAD_URL]
            assert downloaded.text() == "hello world"
            assert downloaded.content_type == "text/plain"
            assert downloaded.filename == "notes.txt"
            assert downloaded.source_url == DOWNLOAD_URL

    async def test_re_fetches_on_each_call(self) -> None:
        async with _personal_file([_json_body("a"), _json_body("b")]) as (file, calls):
            assert (await file.download()).text() == "a"
            assert (await file.download()).text() == "b"
            assert len(calls) == 2

    async def test_falls_back_to_incoming_content_type_when_response_omits_one(self) -> None:
        async with _personal_file([_json_body("bytes")], content_type="application/pdf") as (file, _):
            assert (await file.download()).content_type == "application/pdf"


class TestTextReader:
    async def test_decodes_the_downloaded_bytes(self) -> None:
        async with _personal_file([_json_body("hello")]) as (file, _):
            assert await file.text() == "hello"


class TestExpiredDownloadUrl:
    async def test_raises_first_fetch_when_the_first_fetch_is_unauthorized(self) -> None:
        async with _personal_file([httpx.Response(401)]) as (file, _):
            with pytest.raises(FileUrlExpiredError) as error:
                await file.download()
            assert error.value.reason == "first_fetch"

    async def test_treats_403_the_same_as_401(self) -> None:
        async with _personal_file([httpx.Response(403)]) as (file, _):
            with pytest.raises(FileUrlExpiredError):
                await file.download()

    async def test_raises_reread_when_a_later_fetch_lapses_after_success(self) -> None:
        async with _personal_file([_json_body("first read ok"), httpx.Response(401)]) as (file, _):
            assert (await file.download()).text() == "first read ok"
            with pytest.raises(FileUrlExpiredError) as error:
                await file.download()
            assert error.value.reason == "reread"


class TestStream:
    async def test_yields_the_raw_uncapped_body_chunks(self) -> None:
        async with _personal_file([_json_body("streamed")]) as (file, _):
            chunks = [chunk async for chunk in file.stream()]
            assert b"".join(chunks).decode() == "streamed"


class TestUnsupportedScope:
    async def test_raises_for_group_chat_files(self) -> None:
        async with _personal_file([_json_body("unused")], scope="groupChat") as (file, _):
            with pytest.raises(FileScopeNotSupportedError) as error:
                await file.download()
            assert error.value.scope == "groupChat"


class TestDownloadFailures:
    async def test_raises_when_a_personal_file_has_no_download_url(self) -> None:
        async with _personal_file([_json_body("unused")], download_url=None) as (file, calls):
            with pytest.raises(RuntimeError, match="no download URL"):
                await file.download()
            assert len(calls) == 0

    async def test_raises_when_a_personal_file_download_url_is_not_https(self) -> None:
        async with _personal_file([_json_body("unused")], download_url="http://dl.example/x") as (file, calls):
            with pytest.raises(RuntimeError, match="must use https"):
                await file.download()
            assert len(calls) == 0

    async def test_raises_on_a_non_auth_error_response(self) -> None:
        async with _personal_file([httpx.Response(500)]) as (file, _):
            with pytest.raises(RuntimeError, match="failed to download file: 500"):
                await file.download()


class TestSaveAs:
    async def test_streams_the_bytes_straight_to_a_local_file(self, tmp_path: Path) -> None:
        async with _personal_file([_json_body("saved contents")]) as (file, _):
            path = tmp_path / "out.txt"
            await file.save_as(str(path))
            assert path.read_text() == "saved contents"

    async def test_writes_a_buffered_snapshot_without_re_fetching(self, tmp_path: Path) -> None:
        async with _personal_file([_json_body("snapshot bytes")]) as (file, calls):
            downloaded = await file.download()
            path = tmp_path / "snapshot.txt"
            await downloaded.save_as(str(path))
            assert path.read_text() == "snapshot bytes"
            assert len(calls) == 1
