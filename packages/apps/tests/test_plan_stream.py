"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from microsoft_teams.api import (
    Account,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    PlanInfoEntity,
    Step,
)
from microsoft_teams.apps import ActivityContext, HttpStream, Plan
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


@pytest.mark.parametrize("reply_to_id", [None, "other-prompt"])
async def test_completion_preserves_plan_prompt(streamed, reply_to_id):
    stream, requests, _ = streamed
    ref = stream._ref
    incoming = MessageActivity(
        id="prompt",
        text="Question",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ref.conversation,
    )
    ctx = ActivityContext(incoming, "app", MagicMock(), stream._client, None, ref, False, "oauth", None)
    ctx._stream = stream
    plan = (
        ctx.plan()
        if reply_to_id is None
        else Plan(conversation_id=ref.conversation.id, reply_to_id=reply_to_id, api_client=ctx.api)
    )
    await plan.start([Step(id="lookup", version=1, title="Lookup", status="active")])
    ctx.stream.emit("Answer")
    await stream._pending
    ctx.stream.emit(MessageActivityInput(reply_to_id=reply_to_id, entities=[PlanInfoEntity(plan_type="complete")]))

    result = await ctx.stream.close()

    assert result is not None
    expected_prompt = incoming.id if reply_to_id is None else reply_to_id
    assert result.activity_params.reply_to_id == expected_prompt
    assert all(method == "POST" for method, _ in requests)
    plan_activities = [
        payload
        for _, payload in requests
        if any(entity["type"] == "planInfo" for entity in payload.get("entities", []))
    ]
    assert [
        entity["planType"]
        for payload in plan_activities
        for entity in payload["entities"]
        if entity["type"] == "planInfo"
    ] == ["start", "complete"]
    assert all(payload["replyToId"] == expected_prompt for payload in plan_activities)
    assert ref.activity_id == "prompt"


async def test_plan_conflict_is_not_retried(streamed, monkeypatch):
    stream, requests, responses = streamed
    stream.emit(MessageActivityInput(text="Answer", entities=[PlanInfoEntity(plan_type="complete")]))
    await stream._pending
    error_body = {
        "error": {
            "code": "PlanConflict",
            "message": "The user stopped this plan. It can no longer be updated or completed.",
        }
    }
    responses.append(httpx.Response(409, json=error_body))
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    with pytest.raises(httpx.HTTPStatusError) as error:
        await stream.close()

    assert error.value.response.status_code == 409
    assert error.value.response.json() == error_body
    assert len(requests) == 2
    assert requests[-1][1]["type"] == "message"
    sleep.assert_not_awaited()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(409, json={"error": {"code": "OtherConflict"}}),
        httpx.Response(503, json={"error": {"code": "PlanConflict"}}),
        httpx.Response(409, json={"error": None}),
        httpx.Response(409),
    ],
)
async def test_other_errors_still_retry(streamed, monkeypatch, response):
    stream, requests, responses = streamed
    stream.emit(MessageActivityInput(text="Answer", entities=[PlanInfoEntity(plan_type="complete")]))
    await stream._pending
    responses.append(response)
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    result = await stream.close()

    assert result is not None
    assert result.id == "stream-id"
    assert len(requests) == 3
    sleep.assert_awaited_once()


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
