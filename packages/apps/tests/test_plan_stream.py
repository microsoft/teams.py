"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
import json
import runpy
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from microsoft_teams.api import (
    Account,
    ApiClient,
    ChannelData,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    PlanInfoEntity,
    Step,
    UnknownEntity,
)
from microsoft_teams.apps import ActivityContext, HttpStream, Plan
from microsoft_teams.apps.plugins import StreamTimedOutError
from microsoft_teams.apps.plugins.streamer import PlanConflictStreamError
from microsoft_teams.cards import AdaptiveCard, TextBlock
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


@pytest.mark.parametrize("use_helper", [False, True])
async def test_completion_metadata_is_sent_only_on_final_message(streamed, use_helper):
    stream, requests, _ = streamed
    plan = Plan(conversation_id="chat", reply_to_id="prompt", api_client=stream._client)
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    completion = (
        plan.completion() if use_helper else MessageActivityInput(entities=[PlanInfoEntity(plan_type="complete")])
    )
    completion.with_text_format("markdown").add_entity(
        UnknownEntity.model_validate({"type": "appMetadata", "value": "kept"})
    )
    stream.emit("Here is ")
    stream.emit("the answer.")
    stream.emit(completion)

    assert not stream.closed
    result = await stream.close()

    assert result is not None
    assert result.id == "stream-id"
    assert len(requests) == 2
    assert all(method == "POST" and payload["replyToId"] == "prompt" for method, payload in requests)
    chunk, final = [payload for _, payload in requests]
    assert chunk["type"] == "typing"
    assert all(entity["type"] not in ("planInfo", "appMetadata") for entity in chunk["entities"])
    assert final["type"] == "message"
    assert final["id"] == "stream-id"
    assert final["text"] == "Here is the answer."
    assert final["textFormat"] == "markdown"
    assert [entity for entity in final["entities"] if entity["type"] == "planInfo"] == [
        {"type": "planInfo", "planType": "complete"}
    ]
    assert {"type": "appMetadata", "value": "kept"} in final["entities"]
    assert any(entity["type"] == "streaminfo" and entity["streamType"] == "final" for entity in final["entities"])
    on_sent.assert_not_called()


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
    ctx.stream.emit(plan.completion())

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


@pytest.mark.parametrize("restart", ["emit", "update"])
async def test_final_plan_conflict_retires_cycle_and_allows_reuse(streamed, monkeypatch, restart):
    stream, requests, responses = streamed
    plan = Plan(conversation_id="chat", reply_to_id="prompt", api_client=stream._client)
    on_close = MagicMock()
    stream.on_close(on_close)
    completion = plan.completion().add_card(AdaptiveCard(body=[TextBlock(text="Rejected card")]))
    completion.add_entity(UnknownEntity.model_validate({"type": "appMetadata", "value": "rejected"}))
    completion.with_channel_data(ChannelData.model_validate({"tenant": {"id": "rejected-tenant"}}))
    stream.emit("Rejected answer")
    stream.emit(completion)
    await stream._pending
    error_body = {
        "error": {
            "code": "PlanConflict",
            "message": "The user stopped this plan. It can no longer be updated or completed.",
        }
    }
    response = httpx.Response(409, json=error_body)
    responses.append(response)
    send = stream._send
    raised = []

    async def record_send(activity):
        try:
            return await send(activity)
        except PlanConflictStreamError as error:
            raised.append(error)
            raise

    monkeypatch.setattr(stream, "_send", record_send)
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    with pytest.raises(PlanConflictStreamError) as error:
        await stream.close()

    assert raised == [error.value]
    assert raised[0] is error.value
    assert error.value.response is response
    assert error.value.response.status_code == 409
    assert error.value.response.json() == error_body
    cause = error.value.__cause__
    assert isinstance(cause, httpx.HTTPStatusError)
    assert cause.response is response
    assert cause.request is error.value.request
    assert str(error.value) == str(cause)
    assert len(requests) == 2
    assert requests[-1][1]["type"] == "message"
    sleep.assert_not_awaited()
    assert not stream.closed
    assert not stream.canceled
    assert not stream.timed_out
    assert stream._retired
    assert stream.count == 0
    assert stream.sequence == 1
    assert stream._id is None
    assert stream._text == ""
    assert stream._final_activity is None
    assert stream._channel_data == ChannelData()

    assert await stream.close() is None
    assert await stream.close() is None
    assert len(requests) == 2
    on_close.assert_not_called()

    responses.append(httpx.Response(201, json={"id": "fresh-stream"}))
    if restart == "update":
        stream.update("Fresh status")
        await stream._pending
    stream.emit("Fresh answer")
    result = await stream.close()

    assert result is not None
    assert result.id == "fresh-stream"
    assert stream.closed
    assert await stream.close() is result
    on_close.assert_called_once_with(result)
    fresh_requests = [payload for _, payload in requests[2:]]
    first, final = fresh_requests[0], fresh_requests[-1]
    assert "id" not in first
    stream_type = "informative" if restart == "update" else "streaming"
    assert first["entities"] == [{"type": "streaminfo", "streamType": stream_type, "streamSequence": 1}]
    assert final["id"] == "fresh-stream"
    assert final["text"] == "Fresh answer"
    assert not final.get("attachments")
    assert final["entities"] == [{"type": "streaminfo", "streamType": "final", "streamId": "fresh-stream"}]
    assert final["channelData"] == {"streamId": "fresh-stream", "streamType": "final"}
    assert all(method == "POST" for method, _ in requests)


async def test_final_conflict_without_plan_keeps_buffer(streamed):
    stream, requests, responses = streamed
    stream.emit("Ordinary answer")
    await stream._pending
    responses.append(httpx.Response(409, json={"error": {"code": "PlanConflict"}}))

    with pytest.raises(PlanConflictStreamError):
        await stream.close()

    assert not stream._retired
    result = await stream.close()
    assert result is not None
    assert result.activity_params.text == "Ordinary answer"
    assert len(requests) == 3


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(409, json={"error": {"code": "OtherConflict"}}),
        httpx.Response(503, json={"error": {"code": "PlanConflict"}}),
        httpx.Response(409, json={"error": None}),
        httpx.Response(409),
    ],
)
@pytest.mark.parametrize("exhaust_retries", [False, True])
async def test_other_errors_still_retry(streamed, monkeypatch, response, exhaust_retries):
    stream, requests, responses = streamed
    stream.emit(MessageActivityInput(text="Answer", entities=[PlanInfoEntity(plan_type="complete")]))
    await stream._pending
    attempts = 5 if exhaust_retries else 1
    responses.extend(httpx.Response(response.status_code, content=response.content) for _ in range(attempts))
    sleep = AsyncMock()
    monkeypatch.setattr(asyncio, "sleep", sleep)

    if exhaust_retries:
        with pytest.raises(httpx.HTTPStatusError) as error:
            await stream.close()
        assert error.value.response.status_code == response.status_code
        assert not stream._retired
        assert not stream.closed
        assert len(requests) == 6
        assert sleep.await_count == 4
        sleep.reset_mock()

    result = await stream.close()

    assert result is not None
    assert result.id == "stream-id"
    assert result.activity_params.text == "Answer"
    assert len(requests) == (7 if exhaust_retries else 3)
    if exhaust_retries:
        sleep.assert_not_awaited()
    else:
        sleep.assert_awaited_once()


@pytest.mark.parametrize("timeout_during_chunk", [False, True])
async def test_plan_timeout_never_falls_back_to_update(streamed, timeout_during_chunk):
    stream, requests, responses = streamed
    plan = Plan(conversation_id="chat", reply_to_id="prompt", api_client=stream._client)
    stream.emit(plan.completion().with_text("Answer"))
    await stream._pending
    responses.append(
        httpx.Response(403, json={"error": {"code": "ServiceError", "message": "exceeded streaming time"}})
    )
    if timeout_during_chunk:
        stream.emit(plan.completion().with_text(" continued"))
        await stream._pending

    with pytest.raises(StreamTimedOutError):
        await stream.close()

    assert not responses
    assert len(requests) == 2
    assert all(method == "POST" for method, _ in requests)
    assert requests[-1][1]["type"] == ("typing" if timeout_during_chunk else "message")
    assert stream.timed_out
    assert not stream.canceled
    assert not stream.closed
    assert stream._retired
    assert stream._final_activity is None
    assert stream._text == ""
    assert stream._id is None
    assert stream._channel_data == ChannelData()
    assert stream.count == 0
    assert stream.sequence == 1
    assert await stream.close() is None
    assert await stream.close() is None
    assert stream.timed_out
    assert len(requests) == 2

    stream.update("Fresh status")
    assert not stream.timed_out
    assert not stream._retired
    await stream._pending
    stream.emit("Fresh answer")
    result = await stream.close()
    assert result is not None
    assert result.activity_params.text == "Fresh answer"
    assert all(entity.type != "planInfo" for entity in result.activity_params.entities)


async def test_complete_stream_sample_uses_completion_helper(streamed, monkeypatch):
    stream, requests, _ = streamed
    sample_path = Path(__file__).resolve().parents[3] / "examples" / "plan" / "src" / "main.py"
    sample = runpy.run_path(str(sample_path))
    ref = stream._ref
    incoming = MessageActivity(
        id=ref.activity_id,
        text="complete-stream",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ref.conversation,
    )
    ctx = ActivityContext(incoming, "app", MagicMock(), stream._client, None, ref, False, "oauth", None)
    ctx._stream = stream
    plan = ctx.plan()
    sleep = asyncio.sleep

    async def skip_delay(_):
        await sleep(0)

    monkeypatch.setattr(asyncio, "sleep", skip_delay)
    with patch.object(Plan, "completion", autospec=True, side_effect=Plan.completion) as completion:
        await sample["handle_complete_stream"](ctx)

    completion.assert_called_once_with(plan)
    assert stream.closed
    assert all(method == "POST" and payload["replyToId"] == ref.activity_id for method, payload in requests)
    assert [
        entity["planType"]
        for _, payload in requests
        for entity in payload.get("entities", [])
        if entity["type"] == "planInfo"
    ] == ["start", "continue", "continue", "continue", "complete"]
    final = requests[-1][1]
    assert final["type"] == "message"
    assert final["text"] == "Here is the answer based on the sources."
    assert any(entity["type"] == "streaminfo" and entity["streamType"] == "final" for entity in final["entities"])
