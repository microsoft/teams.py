"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json

import httpx
import pytest
from microsoft_teams.api import (
    Account,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    MessageActivityInput,
    PlanInfoEntity,
)
from microsoft_teams.apps import HttpStream
from microsoft_teams.apps.plugins import StreamTimedOutError
from microsoft_teams.common.http import Client


@pytest.fixture
async def streamed():
    requests = []
    responses = []

    def handle(request):
        requests.append((request.method, json.loads(request.content)))
        return responses.pop(0) if responses else httpx.Response(201, json={"id": "stream-id"})

    ref = ConversationReference(
        bot=Account(id="bot"),
        conversation=ConversationAccount(id="chat"),
        activity_id="prompt",
        service_url="https://example.com",
        channel_id="msteams",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        yield HttpStream(ApiClient(ref.service_url, Client(_http=http)), ref), requests, responses


async def test_completion_metadata_is_sent_only_on_final_message(streamed):
    stream, requests, _ = streamed
    stream.emit("Here is ")
    stream.emit("the answer.")
    stream.emit(MessageActivityInput(entities=[PlanInfoEntity(plan_type="complete")]))

    result = await stream.close()

    assert result is not None
    assert result.id == "stream-id"
    assert len(requests) == 2
    assert all(method == "POST" and payload["replyToId"] == "prompt" for method, payload in requests)
    chunk, final = [payload for _, payload in requests]
    assert chunk["type"] == "typing"
    assert all(entity["type"] != "planInfo" for entity in chunk["entities"])
    assert final["type"] == "message"
    assert final["id"] == "stream-id"
    assert final["text"] == "Here is the answer."
    assert [entity for entity in final["entities"] if entity["type"] == "planInfo"] == [
        {"type": "planInfo", "planType": "complete"}
    ]
    assert any(entity["type"] == "streaminfo" and entity["streamType"] == "final" for entity in final["entities"])


@pytest.mark.parametrize("timeout_during_chunk", [False, True])
async def test_plan_timeout_never_falls_back_to_update(streamed, timeout_during_chunk):
    stream, requests, responses = streamed
    stream.emit(MessageActivityInput(text="Answer", entities=[PlanInfoEntity(plan_type="complete")]))
    await stream._pending
    responses.append(
        httpx.Response(403, json={"error": {"code": "ServiceError", "message": "exceeded streaming time"}})
    )
    if timeout_during_chunk:
        stream.emit(MessageActivityInput(text=" continued", entities=[PlanInfoEntity(plan_type="complete")]))
        await stream._pending

    with pytest.raises(StreamTimedOutError):
        await stream.close()

    assert not responses
    assert len(requests) == 2
    assert all(method == "POST" for method, _ in requests)
    assert requests[-1][1]["type"] == ("typing" if timeout_during_chunk else "message")
