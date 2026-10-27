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
from microsoft_teams.apps import ActivityContext, ActivitySentEvent, Plan
from microsoft_teams.apps.activity_send import send_or_update_activity
from microsoft_teams.common.experimental import ExperimentalWarning
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


def test_plan_constructor_emits_preview_warning(api, ref):
    with pytest.warns(ExperimentalWarning, match="Plan.*ExperimentalTeamsPlan"):
        Plan(api, ref, reply_to_id="prompt")
    api.conversations.create_activity.assert_not_called()


def test_factory_emits_preview_warning_for_cached_helper(api, ref):
    activity = MessageActivity(
        id="prompt",
        text="Question",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ref.conversation,
    )
    ctx = ActivityContext(activity, "app", MagicMock(), api, None, ref, False, "oauth", None)
    with pytest.warns(ExperimentalWarning, match="ExperimentalTeamsPlan") as caught:
        plan = ctx.plan()
    assert any("ActivityContext.plan" in str(warning.message) for warning in caught)
    with pytest.warns(ExperimentalWarning, match=r"ActivityContext\.plan.*ExperimentalTeamsPlan") as caught:
        assert ctx.plan() is plan
    assert len(caught) == 1


@pytest.mark.parametrize(
    "method,operation", [("start", "start"), ("update", "continue"), ("stop", "stop"), ("error", "error")]
)
async def test_controls_send_prompt_bound_typing_activity(api, ref, method, operation):
    plan = Plan(api, ref, reply_to_id="original-prompt")
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
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
    on_sent.assert_called_once()
    event = on_sent.call_args.args[0]
    assert isinstance(event, ActivitySentEvent)
    assert event.activity.id == "DO_NOT_USE_PLACEHOLDER_ID"
    assert event.activity.activity_params == activity
    assert event.conversation_ref == ref
    assert event.conversation_ref is not ref


async def test_complete_string_adds_completion_entity(api, ref):
    plan = Plan(api, ref, reply_to_id="prompt")
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    result = await plan.complete_plan("Done")

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
    on_sent.assert_called_once_with(ActivitySentEvent(activity=result, conversation_ref=ref))
    assert on_sent.call_args.args[0].activity is result


@pytest.mark.parametrize("method", ["start", "complete_plan"])
async def test_failed_send_does_not_emit_sent(api, ref, method):
    plan = Plan(api, ref, reply_to_id="prompt")
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    api.conversations.create_activity.side_effect = RuntimeError("Plan send failed")

    with pytest.raises(RuntimeError, match="Plan send failed"):
        if method == "start":
            await plan.start([Step(id="lookup", version=1, title="Lookup", status="active")])
        else:
            await plan.complete_plan("Done")

    api.conversations.create_activity.assert_awaited_once()
    on_sent.assert_not_called()


async def test_rejected_completion_does_not_emit_sent(api, ref):
    plan = Plan(api, ref, reply_to_id="prompt")
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)

    with pytest.raises(ValueError, match="non-complete"):
        await plan.complete_plan(MessageActivityInput(text="Done", entities=[PlanInfoEntity(plan_type="stop")]))

    api.conversations.create_activity.assert_not_awaited()
    on_sent.assert_not_called()


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
    expected_ref = ref.model_copy(deep=True)
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    ref.conversation.id = "changed"
    ref.bot.id = "changed"

    result = await plan.complete_plan("Done")

    conversation_id, activity = api.conversations.create_activity.call_args.args
    assert conversation_id == "chat"
    assert activity.conversation.id == "chat"
    assert activity.from_.id == "bot"
    on_sent.assert_called_once_with(ActivitySentEvent(activity=result, conversation_ref=expected_ref))

    event = on_sent.call_args.args[0]
    event.conversation_ref.conversation.id = "changed-by-listener"
    event.conversation_ref.bot.is_targeted = True
    await plan.stop()

    assert on_sent.call_count == 2
    next_event = on_sent.call_args.args[0]
    assert next_event.conversation_ref == expected_ref
    assert next_event.conversation_ref.conversation is not event.conversation_ref.conversation
    conversation_id, activity = api.conversations.create_activity.call_args.args
    assert conversation_id == "chat"
    assert activity.conversation.id == "chat"
    assert activity.from_.is_targeted is None


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
