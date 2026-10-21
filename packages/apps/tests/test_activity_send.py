"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.api import (
    Account,
    AgenticIdentity,
    ConversationAccount,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
)
from microsoft_teams.apps.activity_send import send_or_update_activity

SERVICE_URL = "https://service.example"


def _sent(id: str) -> SentActivity:
    return SentActivity(id=id, activity_params=MessageActivityInput(text="sent"))


def _api() -> MagicMock:
    api = MagicMock()
    api.service_url = SERVICE_URL
    api.clone.return_value = api
    conversations = api.conversations
    conversations.create_activity = AsyncMock(return_value=_sent("created"))
    conversations.update_activity = AsyncMock(return_value=_sent("updated"))
    conversations.create_targeted_activity = AsyncMock(return_value=_sent("created-targeted"))
    conversations.update_targeted_activity = AsyncMock(return_value=_sent("updated-targeted"))
    conversations._create_reply_chain_activity = AsyncMock(return_value=_sent("reply"))
    conversations._create_targeted_reply_chain_activity = AsyncMock(return_value=_sent("reply-targeted"))
    return api


def _ref() -> ConversationReference:
    return ConversationReference(
        bot=Account(id="bot-id", name="Bot"),
        conversation=ConversationAccount(id="chat-1"),
        channel_id="msteams",
        service_url=SERVICE_URL,
    )


def _targeted() -> MessageActivityInput:
    return MessageActivityInput(text="hello").with_recipient(
        Account(id="user-1", name="User", role="user"), is_targeted=True
    )


@pytest.mark.asyncio
class TestSendWithReplyChainId:
    async def test_replies_in_the_reply_chain_of_the_conversation_in_the_reference(self):
        api = _api()
        ref = _ref()

        result = await send_or_update_activity(api, MessageActivityInput(text="hello"), ref, reply_chain_id="root-1")

        reply = api.conversations._create_reply_chain_activity
        reply.assert_called_once()
        assert reply.call_args.args[:2] == ("chat-1", "root-1")
        sent = reply.call_args.args[2]
        assert sent.text == "hello"
        assert sent.from_ == ref.bot
        assert sent.conversation == ref.conversation
        api.conversations.create_activity.assert_not_called()
        assert result.id == "reply"

    async def test_replies_with_a_targeted_activity_in_the_reply_chain(self):
        api = _api()

        result = await send_or_update_activity(api, _targeted(), _ref(), reply_chain_id="root-1")

        reply_targeted = api.conversations._create_targeted_reply_chain_activity
        reply_targeted.assert_called_once()
        assert reply_targeted.call_args.args[:2] == ("chat-1", "root-1")
        api.conversations._create_reply_chain_activity.assert_not_called()
        api.conversations.create_targeted_activity.assert_not_called()
        assert result.id == "reply-targeted"

    async def test_ignores_the_reply_chain_id_when_updating_an_existing_activity(self):
        api = _api()
        activity = MessageActivityInput(text="edited")
        activity.id = "existing-1"

        await send_or_update_activity(api, activity, _ref(), reply_chain_id="root-1")

        api.conversations.update_activity.assert_called_once()
        assert api.conversations.update_activity.call_args.args[:2] == ("chat-1", "existing-1")
        api.conversations._create_reply_chain_activity.assert_not_called()

    async def test_ignores_the_reply_chain_id_when_updating_an_existing_targeted_activity(self):
        api = _api()
        activity = _targeted()
        activity.id = "existing-1"

        await send_or_update_activity(api, activity, _ref(), reply_chain_id="root-1")

        api.conversations.update_targeted_activity.assert_called_once()
        api.conversations._create_targeted_reply_chain_activity.assert_not_called()

    async def test_keeps_the_agentic_identity_when_replying_in_the_reply_chain(self):
        api = _api()
        identity = AgenticIdentity(
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )

        await send_or_update_activity(
            api, MessageActivityInput(text="hello"), _ref(), agentic_identity=identity, reply_chain_id="root-1"
        )

        api.clone.assert_called_once_with(service_url=SERVICE_URL, agentic_identity=identity)
        api.conversations._create_reply_chain_activity.assert_called_once()

    async def test_creates_a_root_activity_without_a_reply_chain_id(self):
        api = _api()

        await send_or_update_activity(api, MessageActivityInput(text="hello"), _ref())

        api.conversations.create_activity.assert_called_once()
        api.conversations._create_reply_chain_activity.assert_not_called()
        api.conversations._create_targeted_reply_chain_activity.assert_not_called()
