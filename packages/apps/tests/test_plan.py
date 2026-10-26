"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from microsoft_teams.api import (
    Account,
    AgenticIdentity,
    ApiClient,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    PlanInfoEntity,
    SentActivity,
    Step,
    UnknownEntity,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.apps import ActivityContext, Plan
from microsoft_teams.apps.activity_send import send_or_update_activity
from microsoft_teams.common.http import Client


@pytest.fixture
def ref():
    return ConversationReference(
        activity_id="prompt",
        bot=Account(id="bot"),
        conversation=ConversationAccount(id="chat"),
        channel_id="msteams",
        service_url="https://example.com",
    )


@pytest.fixture
def api(ref):
    client = MagicMock(spec=ApiClient)
    client.service_url = ref.service_url
    client.from_service_url.return_value = client

    async def create_activity(conversation_id, activity):
        activity_id = "answer" if isinstance(activity, MessageActivityInput) else "DO_NOT_USE_PLACEHOLDER_ID"
        return SentActivity(id=activity_id, activity_params=activity)

    async def update_activity(conversation_id, activity_id, activity):
        return SentActivity(id=activity_id, activity_params=activity)

    client.conversations = MagicMock()
    client.conversations.create_activity = AsyncMock(side_effect=create_activity)
    client.conversations.update_activity = AsyncMock(side_effect=update_activity)
    return client


@pytest.mark.parametrize(
    "method,operation", [("start", "start"), ("update", "continue"), ("stop", "stop"), ("error", "error")]
)
async def test_controls_send_prompt_bound_typing_activity(api, ref, method, operation):
    plan = Plan(api, ref, reply_to_id="original-prompt")
    steps = [Step(id="lookup", version=1, title="Lookup", status="active")]
    expected_entity = {"type": "planInfo", "planType": operation}
    if method in ("start", "update"):
        result = await getattr(plan, method)(steps)
        expected_entity["steps"] = [step.model_dump(exclude_none=True) for step in steps]
    else:
        result = await getattr(plan, method)()

    assert result is None
    api.conversations.create_activity.assert_awaited_once()
    conversation_id, activity = api.conversations.create_activity.call_args.args
    assert conversation_id == "chat"
    assert activity.model_dump(by_alias=True, exclude_none=True) == {
        "type": "typing",
        "replyToId": "original-prompt",
        "from": {"id": "bot"},
        "conversation": {"id": "chat"},
        "entities": [expected_entity],
    }


async def test_complete_string_adds_completion_entity(api, ref):
    result = await Plan(api, ref, reply_to_id="prompt").complete_plan("Done")

    api.conversations.create_activity.assert_awaited_once()
    conversation_id, activity = api.conversations.create_activity.call_args.args
    assert conversation_id == "chat"
    assert isinstance(activity, MessageActivityInput)
    assert activity.text == "Done"
    assert activity.reply_to_id == "prompt"
    assert activity.from_ == ref.bot
    assert activity.conversation == ref.conversation
    assert activity.entities == [PlanInfoEntity(plan_type="complete")]
    assert result.id == "answer"
    assert result.activity_params == activity


@pytest.mark.parametrize("has_completion_entity", [False, True])
async def test_complete_message_preserves_metadata_without_mutating_input(api, ref, has_completion_entity):
    message = MessageActivityInput(
        text="Done",
        text_format="markdown",
        reply_to_id="other",
        entities=[UnknownEntity.model_validate({"type": "appMetadata", "value": "kept"})],
    )
    if has_completion_entity:
        message.add_entity(PlanInfoEntity(plan_type="complete"))
    original = message.model_dump()

    await Plan(api, ref, reply_to_id="prompt").complete_plan(message)

    api.conversations.create_activity.assert_awaited_once()
    activity = api.conversations.create_activity.call_args.args[1]
    assert activity.text == "Done"
    assert activity.text_format == "markdown"
    assert activity.reply_to_id == "prompt"
    assert [entity.model_dump() for entity in activity.entities] == [
        {"type": "appMetadata", "value": "kept"},
        PlanInfoEntity(plan_type="complete").model_dump(),
    ]
    assert message.model_dump() == original


async def test_factory_defaults_to_prompt_not_parent_and_caches_by_prompt(api, ref):
    activity = MessageActivity(
        id="prompt",
        reply_to_id="parent",
        text="Question",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ref.conversation,
    )
    ctx = ActivityContext(activity, "app", MagicMock(), api, None, ref, False, "oauth", None)
    original = ctx.plan()
    other = ctx.plan(reply_to_id="other")
    assert original is ctx.plan(reply_to_id="prompt")
    assert other is ctx.plan(reply_to_id="other")
    assert other is not original

    await original.stop()
    await other.stop()

    assert [call.args[1].reply_to_id for call in api.conversations.create_activity.call_args_list] == [
        "prompt",
        "other",
    ]


async def test_helper_copies_conversation_reference(api, ref):
    plan = Plan(api, ref, reply_to_id="prompt")
    ref.conversation.id = "changed"
    ref.bot.id = "changed"

    await plan.complete_plan("Done")

    conversation_id, activity = api.conversations.create_activity.call_args.args
    assert conversation_id == "chat"
    assert activity.conversation.id == "chat"
    assert activity.from_.id == "bot"


async def test_plan_preserves_scoped_caller_when_using_saved_service_url(ref):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx.Response(202)

    provider = MagicMock(
        spec=["get_app_token", "get_agentic_app_token"],
        get_app_token=MagicMock(),
        get_agentic_app_token=MagicMock(return_value="test-agent-token"),
    )
    identity = AgenticIdentity(
        agentic_app_blueprint_id="blueprint",
        agentic_app_id="agent",
        tenant_id="tenant",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http:
        client = ApiClient(
            "https://different.example.com",
            Client(_http=http),
            token_provider=provider,
            agentic_identity=identity,
        )
        await Plan(client, ref, reply_to_id="prompt").stop()

    assert len(requests) == 1
    assert requests[0].url.host == "example.com"
    provider.get_app_token.assert_not_called()
    provider.get_agentic_app_token.assert_called_once_with(PUBLIC.agent_bot_scope, "agent", "tenant")


@pytest.mark.parametrize("streamed", [False, True])
async def test_send_routes_plan_with_existing_id_to_create_not_update(api, ref, streamed):
    activity = MessageActivityInput(
        id="answer",
        text="Done",
        reply_to_id="prompt",
        entities=[PlanInfoEntity(plan_type="complete")],
    )
    if streamed:
        activity.add_stream_final()

    result = await send_or_update_activity(api, activity, ref)

    api.conversations.create_activity.assert_awaited_once_with("chat", activity)
    api.conversations.update_activity.assert_not_awaited()
    assert result.id == "answer"
