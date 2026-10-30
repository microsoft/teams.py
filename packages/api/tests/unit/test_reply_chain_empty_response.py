"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import httpx
import pytest
from microsoft_teams.api import ApiClient, TypingActivityInput
from microsoft_teams.common.http import Client


@pytest.fixture
async def transport():
    requests = []
    responses = []

    def handle(request):
        requests.append(request)
        return responses.pop(0) if responses else httpx.Response(202)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        yield ApiClient("https://example.com", Client(_http=http)), requests, responses


@pytest.mark.unit
class TestReplyChainWithoutResponseId:
    @pytest.mark.parametrize("response", [httpx.Response(202), httpx.Response(200, json={})])
    @pytest.mark.parametrize("targeted", [False, True])
    async def test_typing_without_an_id_in_the_response_returns_the_placeholder(self, transport, response, targeted):
        api, requests, responses = transport
        responses.append(response)
        activity = TypingActivityInput()

        if targeted:
            result = await api.conversations._create_targeted_reply_chain_activity("chat-1", "root-1", activity)
        else:
            result = await api.conversations._create_reply_chain_activity("chat-1", "root-1", activity)

        assert result.id == "DO_NOT_USE_PLACEHOLDER_ID"
        assert result.activity_params == activity
        assert requests[0].url.path == "/v3/conversations/chat-1/replyChains/root-1"
