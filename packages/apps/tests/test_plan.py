"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import json
from unittest.mock import AsyncMock, MagicMock

import httpx2
import pytest
from microsoft_teams.api import (
    Account,
    AgenticIdentity,
    ApiClient,
    ChannelData,
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
from microsoft_teams.apps import ActivityContext, Plan, PlanOptions
from microsoft_teams.apps.activity_send import send_or_update_activity
from microsoft_teams.cards import AdaptiveCard, TextBlock
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


@pytest.fixture
def target(ref):
    return {"conversation_id": ref.conversation.id, "reply_to_id": "prompt"}


def test_plan_constructor_emits_preview_warning(api, target):
    options = PlanOptions(**target, api_client=api)
    with pytest.warns(ExperimentalWarning, match="Plan.*ExperimentalTeamsPlan"):
        Plan(**options)
    api.conversations.create_activity.assert_not_called()
    api.from_service_url.assert_not_called()


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
async def test_controls_send_prompt_bound_typing_activity(api, target, method, operation):
    target["reply_to_id"] = "original-prompt"
    plan = Plan(**target, api_client=api)
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
        "conversation": {"id": "chat"},
        "entities": [expected_entity],
    }
    on_sent.assert_called_once()
    sent = on_sent.call_args.args[0]
    assert isinstance(sent, SentActivity)
    assert sent.id == "DO_NOT_USE_PLACEHOLDER_ID"
    assert sent.activity_params == activity


async def test_complete_string_adds_completion_entity(api, ref, target):
    plan = Plan(**target, api_client=api)
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    result = await plan.complete("Done")

    api.conversations.create_activity.assert_awaited_once()
    conversation_id, activity = api.conversations.create_activity.call_args.args
    assert conversation_id == "chat"
    assert isinstance(activity, MessageActivityInput)
    assert activity.text == "Done"
    assert activity.reply_to_id == "prompt"
    assert activity.from_ is None
    assert activity.conversation == ref.conversation
    assert activity.entities == [PlanInfoEntity(plan_type="complete")]
    assert result.id == "answer"
    assert result.activity_params == activity
    on_sent.assert_called_once_with(result)
    assert on_sent.call_args.args[0] is result


def test_completion_builds_prompt_bound_message_without_sending(api, target):
    plan = Plan(**target, api_client=api)
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    original = plan.model_dump()

    activity = plan.completion()

    assert isinstance(activity, MessageActivityInput)
    assert activity.model_dump(by_alias=True, exclude_none=True) == {
        "type": "message",
        "replyToId": "prompt",
        "entities": [{"type": "planInfo", "planType": "complete"}],
    }
    assert plan.model_dump() == original
    api.conversations.create_activity.assert_not_called()
    api.conversations.update_activity.assert_not_called()
    api.from_service_url.assert_not_called()
    on_sent.assert_not_called()


def test_completion_returns_independent_messages_and_entities(api, target):
    plan = Plan(**target, api_client=api)
    first = plan.completion()
    second = plan.completion()
    original = second.model_dump()

    assert first is not second
    assert first.entities is not second.entities
    assert first.entities[0] is not second.entities[0]
    first.with_text("Only the first message").with_text_format("markdown")
    first.add_entity(UnknownEntity.model_validate({"type": "appMetadata", "value": "kept"}))
    first.reply_to_id = "other-prompt"
    first.entities[0].plan_type = "stop"

    assert second.model_dump() == original
    assert plan.completion().model_dump() == original
    assert plan.reply_to_id == "prompt"


@pytest.mark.parametrize("method", ["start", "complete"])
async def test_failed_send_does_not_emit_sent(api, target, method):
    plan = Plan(**target, api_client=api)
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    api.conversations.create_activity.side_effect = RuntimeError("Plan send failed")

    with pytest.raises(RuntimeError, match="Plan send failed"):
        if method == "start":
            await plan.start([Step(id="lookup", version=1, title="Lookup", status="active")])
        else:
            await plan.complete("Done")

    api.conversations.create_activity.assert_awaited_once()
    on_sent.assert_not_called()
    assert plan.model_dump(mode="json", by_alias=False) == target


@pytest.mark.parametrize("operation", ["start", "continue", "stop", "error"])
async def test_rejected_completion_does_not_emit_sent(api, target, operation):
    plan = Plan(**target, api_client=api)
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)
    message = plan.completion().with_text("Done").add_entity(PlanInfoEntity(plan_type=operation))
    original = message.model_dump()

    with pytest.raises(ValueError, match="non-complete"):
        await plan.complete(message)

    api.conversations.create_activity.assert_not_awaited()
    on_sent.assert_not_called()
    assert message.model_dump() == original


@pytest.mark.parametrize("has_completion_entity", [False, True])
async def test_complete_message_preserves_metadata_without_mutating_input(api, target, has_completion_entity):
    plan = Plan(**target, api_client=api)
    card = AdaptiveCard(body=[TextBlock(text="Card answer")])
    channel_data = ChannelData.model_validate({"channel": {"id": "channel"}})
    metadata = UnknownEntity.model_validate({"type": "appMetadata", "value": {"items": ["kept"]}})
    message = plan.completion() if has_completion_entity else MessageActivityInput()
    message.with_text("Done").with_text_format("markdown").add_card(card).with_channel_data(channel_data).add_entity(
        metadata
    )
    message.reply_to_id = "other"
    message.conversation = ConversationAccount(id="other-chat")
    original = message.model_dump()

    await plan.complete(message)

    api.conversations.create_activity.assert_awaited_once()
    activity = api.conversations.create_activity.call_args.args[1]
    assert activity is not message
    assert activity.text == "Done"
    assert activity.text_format == "markdown"
    assert activity.reply_to_id == "prompt"
    assert activity.conversation.id == "chat"
    assert activity.attachments[0].content == card
    assert activity.attachments[0].content is not card
    assert activity.channel_data == channel_data
    assert activity.channel_data is not channel_data
    assert activity.channel_data.channel is not channel_data.channel
    assert metadata in activity.entities
    assert all(entity is not metadata for entity in activity.entities)
    assert [entity for entity in activity.entities if isinstance(entity, PlanInfoEntity)] == [
        PlanInfoEntity(plan_type="complete")
    ]
    assert message.model_dump() == original

    sent_payload = activity.model_dump()
    assert card.body is not None
    card.body.append(TextBlock(text="Caller added"))
    assert channel_data.channel is not None
    channel_data.channel.id = "changed-channel"
    assert metadata.model_extra is not None
    metadata.model_extra["value"]["items"].append("caller-added")
    message.with_text("Caller changed")
    assert activity.model_dump() == sent_payload


async def test_factory_binds_to_incoming_activity_and_caches_one_helper(api, ref):
    ref.activity_id = "different-prompt"
    activity = MessageActivity(
        id="prompt",
        reply_to_id="parent",
        text="Question",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ref.conversation,
    )
    ctx = ActivityContext(activity, "app", MagicMock(), api, None, ref, False, "oauth", None)
    api.from_service_url.assert_not_called()
    with pytest.raises(TypeError, match="reply_to_id"):
        ctx.plan(reply_to_id="other")  # pyright: ignore[reportCallIssue]
    api.from_service_url.assert_not_called()

    plan = ctx.plan()
    assert ctx.plan() is plan
    api.from_service_url.assert_called_once_with(ref.service_url)
    api.conversations.create_activity.assert_not_awaited()

    await plan.stop()

    api.conversations.create_activity.assert_awaited_once()
    assert api.conversations.create_activity.call_args.args[1].reply_to_id == "prompt"


async def test_factory_cache_is_local_to_context(api, ref):
    activity = MessageActivity(
        id="prompt",
        text="Question",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ref.conversation,
    )
    first = ActivityContext(activity, "app", MagicMock(), api, None, ref, False, "oauth", None)
    second = ActivityContext(activity, "app", MagicMock(), api, None, ref, False, "oauth", None)
    plan = first.plan()
    other = second.plan()
    on_sent = MagicMock()
    plan.events.on("sent", on_sent)

    assert plan is first.plan()
    assert other is second.plan()
    assert plan is not other
    await other.stop()
    on_sent.assert_not_called()


@pytest.mark.parametrize("agentic", [False, True])
async def test_plan_uses_runtime_endpoint_and_authenticated_caller(target, agentic):
    requests = []

    def handle(request):
        requests.append(request)
        return httpx2.Response(202)

    provider = MagicMock(
        spec=["get_app_token", "get_agentic_app_token"],
        get_app_token=MagicMock(return_value="test-bot-token"),
        get_agentic_app_token=MagicMock(return_value="test-agent-token"),
    )
    identity = AgenticIdentity(
        agentic_app_blueprint_id="blueprint",
        agentic_app_id="agent",
        tenant_id="tenant",
    )
    async with httpx2.AsyncClient(transport=httpx2.MockTransport(handle)) as http:
        client = ApiClient(
            "https://different.example.com",
            Client(_http=http),
            token_provider=provider,
            agentic_identity=identity if agentic else None,
        )
        await Plan(**target, api_client=client).stop()

    assert len(requests) == 1
    assert requests[0].url.host == "different.example.com"
    assert requests[0].url.path == "/v3/conversations/chat/activities"
    expected_payload = {
        "type": "typing",
        "replyToId": "prompt",
        "conversation": {"id": "chat"},
        "entities": [{"type": "planInfo", "planType": "stop"}],
    }
    assert json.loads(requests[0].content) == expected_payload
    if agentic:
        assert requests[0].headers["authorization"] == "Bearer test-agent-token"
        provider.get_app_token.assert_not_called()
        provider.get_agentic_app_token.assert_called_once_with(PUBLIC.agent_bot_scope, "agent", "tenant")
    else:
        assert requests[0].headers["authorization"] == "Bearer test-bot-token"
        provider.get_app_token.assert_called_once_with(PUBLIC.bot_scope, None)
        provider.get_agentic_app_token.assert_not_called()


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


async def test_plan_serialization_round_trip(api, ref):
    activity = MessageActivity(
        id="original-prompt",
        reply_to_id="parent",
        text="Question",
        from_=Account(id="user"),
        recipient=ref.bot,
        conversation=ConversationAccount(id="chat;messageid=thread-root"),
    )
    ref.conversation = activity.conversation
    ctx = ActivityContext(activity, "app", MagicMock(), api, None, ref, False, "oauth", None)
    original = ctx.plan()
    original.events.on("sent", MagicMock())
    plan_data = json.loads(json.dumps(original.model_dump(mode="json", by_alias=False)))

    assert plan_data == {
        "conversation_id": "chat;messageid=thread-root",
        "reply_to_id": "original-prompt",
    }
    plan_options = PlanOptions(**plan_data, api_client=api)
    restored = Plan(**plan_options)
    assert restored.model_dump(mode="json", by_alias=False) == plan_data
    assert restored.events.listener_count("sent") == 0
    api.conversations.create_activity.assert_not_awaited()

    steps = [Step(id="lookup", version=0, title="Lookup", status="active")]
    await restored.update(steps)
    result = await Plan(**plan_options).complete("Done")

    assert result.id == "answer"
    assert restored.model_dump(mode="json", by_alias=False) == plan_data
    assert original.model_dump(mode="json", by_alias=False) == plan_data
    sent = api.conversations.create_activity.call_args_list
    assert len(sent) == 2
    assert all(call.args[0] == "chat;messageid=thread-root" for call in sent)
    assert all(call.args[1].reply_to_id == "original-prompt" for call in sent)
    assert [call.args[1].entities[0].plan_type for call in sent] == ["continue", "complete"]
    assert sent[0].args[1].entities[0].steps == steps
