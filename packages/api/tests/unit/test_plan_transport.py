"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json

import httpx2
import pytest
from microsoft_teams.api import ApiClient, MessageActivityInput, PlanInfoEntity, PlanType, Step, TypingActivityInput
from microsoft_teams.common.http import Client


@pytest.fixture
async def transport():
    requests = []
    responses = []

    def handle(request):
        requests.append(request)
        return responses.pop(0) if responses else httpx2.Response(202)

    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as http:
        yield ApiClient("https://example.com", Client(_http=http)), requests, responses


@pytest.mark.unit
class TestPlanActivityTransport:
    @pytest.mark.parametrize("operation", ["start", "continue", "stop", "error"])
    @pytest.mark.parametrize("method", ["create", "reply"])
    async def test_empty_control_ack_returns_placeholder(self, transport, operation: PlanType, method):
        api, requests, _ = transport
        steps = (
            [Step(id="lookup", title="Lookup", status="active", version=1)]
            if operation in ("start", "continue")
            else None
        )
        activity = TypingActivityInput(
            reply_to_id="prompt", entities=[PlanInfoEntity(plan_type=operation, steps=steps)]
        )
        client = api.conversations.activities_client
        if method == "reply":
            result = await client.reply("conversation", "prompt", activity)
        else:
            result = await client.create("conversation", activity)

        assert result.id == "DO_NOT_USE_PLACEHOLDER_ID"
        assert result.activity_params == activity
        assert len(requests) == 1
        assert requests[0].method == "POST"
        assert requests[0].url.path == "/v3/conversations/conversation/activities"
        assert json.loads(requests[0].content) == activity.model_dump(by_alias=True, exclude_none=True)

    @pytest.mark.parametrize("method", ["create", "reply"])
    async def test_complete_returns_message_id(self, transport, method):
        api, requests, responses = transport
        responses.append(httpx2.Response(201, json={"id": "answer-id"}))
        activity = MessageActivityInput(
            text="Answer", reply_to_id="prompt", entities=[PlanInfoEntity(plan_type="complete")]
        )
        client = api.conversations.activities_client
        if method == "reply":
            result = await client.reply("conversation", "prompt", activity)
        else:
            result = await client.create("conversation", activity)

        assert result.id == "answer-id"
        assert result.activity_params == activity
        assert len(requests) == 1
        assert requests[0].method == "POST"
        assert json.loads(requests[0].content) == activity.model_dump(by_alias=True, exclude_none=True)

    @pytest.mark.parametrize("method", ["create", "reply"])
    async def test_control_does_not_expose_a_response_activity_id(self, transport, method):
        api, _, responses = transport
        responses.append(httpx2.Response(201, json={"id": "not-a-message"}))
        activity = TypingActivityInput(reply_to_id="prompt", entities=[PlanInfoEntity(plan_type="stop")])
        client = api.conversations.activities_client
        if method == "reply":
            result = await client.reply("conversation", "prompt", activity)
        else:
            result = await client.create("conversation", activity)
        assert result.id == "DO_NOT_USE_PLACEHOLDER_ID"

    async def test_service_error_is_propagated(self, transport):
        api, requests, responses = transport
        error_body = {"error": {"code": "PlanConflict", "message": "Stopped"}}
        responses.append(httpx2.Response(409, json=error_body))
        activity = TypingActivityInput(reply_to_id="prompt", entities=[PlanInfoEntity(plan_type="stop")])

        with pytest.raises(httpx2.HTTPStatusError) as error:
            await api.conversations.create_activity("conversation", activity)

        assert error.value.response.status_code == 409
        assert error.value.response.json() == error_body
        assert len(requests) == 1

    @pytest.mark.parametrize("original_prompt", [None, "original"])
    async def test_reply_supplies_prompt_without_mutating_input(self, transport, original_prompt):
        api, requests, _ = transport
        activity = TypingActivityInput(reply_to_id=original_prompt, entities=[PlanInfoEntity(plan_type="stop")])

        result = await api.conversations.reply_to_activity("conversation", "prompt", activity)

        assert result.id == "DO_NOT_USE_PLACEHOLDER_ID"
        assert result.activity_params == activity
        assert len(requests) == 1
        assert json.loads(requests[0].content)["replyToId"] == "prompt"
        assert activity.reply_to_id == original_prompt
