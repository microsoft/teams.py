"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import (
    Account,
    ChannelData,
    ChannelInfo,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.apps import App, AppOptions
from microsoft_teams.apps.routing.activity_context import ActivityContext


@dataclass
class FakeQueryParameters:
    top: int | None = None


class FakeRepliesBuilder:
    RepliesRequestBuilderGetQueryParameters = FakeQueryParameters

    def __init__(self, value: list[Any]):
        self.get = AsyncMock(return_value=SimpleNamespace(value=value))
        self.request_adapter = FakeRequestAdapter([])


class FakeRequestAdapter:
    def __init__(self, pages: list[Any]):
        self.send_async = AsyncMock(side_effect=pages)


class FakeMessagesBuilder:
    MessagesRequestBuilderGetQueryParameters = FakeQueryParameters

    def __init__(self, value: list[Any], replies_value: list[Any] | None = None):
        self.get = AsyncMock(return_value=SimpleNamespace(value=value))
        self.replies = FakeRepliesBuilder(replies_value or [])
        self.request_adapter = FakeRequestAdapter([])
        self.thread_id: str | None = None

    def by_chat_message_id(self, thread_id: str) -> SimpleNamespace:
        self.thread_id = thread_id
        return SimpleNamespace(replies=self.replies)


class FakeChatsBuilder:
    def __init__(self, messages: FakeMessagesBuilder):
        self.messages = messages
        self.chat_id: str | None = None

    def by_chat_id(self, chat_id: str) -> SimpleNamespace:
        self.chat_id = chat_id
        return SimpleNamespace(messages=self.messages)


class FakeChannelsBuilder:
    def __init__(self, messages: FakeMessagesBuilder):
        self.messages = messages
        self.channel_id: str | None = None

    def by_channel_id(self, channel_id: str) -> SimpleNamespace:
        self.channel_id = channel_id
        return SimpleNamespace(messages=self.messages)


class FakeTeamsBuilder:
    def __init__(self, channels: FakeChannelsBuilder):
        self.channels = channels
        self.team_id: str | None = None

    def by_team_id(self, team_id: str) -> SimpleNamespace:
        self.team_id = team_id
        return SimpleNamespace(channels=self.channels)


class FakeGraph:
    def __init__(self):
        self.chat_messages = FakeMessagesBuilder(["chat-message"], ["chat-reply"])
        self.channel_messages = FakeMessagesBuilder(["channel-message"], ["channel-reply"])
        self.chats = FakeChatsBuilder(self.chat_messages)
        self.channels = FakeChannelsBuilder(self.channel_messages)
        self.teams = FakeTeamsBuilder(self.channels)


@pytest.mark.asyncio
async def test_app_get_history_reads_chat_messages_with_top() -> None:
    app = App(**AppOptions(client_id="test-id", client_secret="test-secret"))
    graph = FakeGraph()

    with patch.object(app, "get_app_graph", return_value=graph):
        result = await app.get_history(n=3, chat_id="chat-id")

    assert result == ["chat-message"]
    assert graph.chats.chat_id == "chat-id"
    config = graph.chat_messages.get.call_args.args[0]
    assert config.query_parameters.top == 3


@pytest.mark.asyncio
async def test_app_get_history_paginates_when_count_exceeds_graph_page_limit() -> None:
    app = App(**AppOptions(client_id="test-id", client_secret="test-secret"))
    graph = FakeGraph()
    graph.chat_messages.get = AsyncMock(
        return_value=SimpleNamespace(value=list(range(50)), odata_next_link="https://graph.example/next")
    )
    graph.chat_messages.request_adapter = FakeRequestAdapter(
        [SimpleNamespace(value=list(range(50, 100)), odata_next_link=None)]
    )

    with patch.object(app, "get_app_graph", return_value=graph):
        result = await app.get_history(n=75, chat_id="chat-id")

    assert result == list(range(75))
    config = graph.chat_messages.get.call_args.args[0]
    assert config.query_parameters.top == 50
    next_request = graph.chat_messages.request_adapter.send_async.call_args.args[0]
    assert next_request.url == "https://graph.example/next"


@pytest.mark.asyncio
async def test_app_get_history_reads_channel_thread_replies() -> None:
    app = App(**AppOptions(client_id="test-id", client_secret="test-secret"))
    graph = FakeGraph()

    with patch.object(app, "get_app_graph", return_value=graph):
        result = await app.get_history(
            n=5,
            team_aad_group_id="team-aad-group-id",
            channel_id="channel-id",
            thread_id="root-message-id",
        )

    assert result == ["channel-reply"]
    assert graph.teams.team_id == "team-aad-group-id"
    assert graph.channels.channel_id == "channel-id"
    assert graph.channel_messages.thread_id == "root-message-id"
    config = graph.channel_messages.replies.get.call_args.args[0]
    assert config.query_parameters.top == 5


@pytest.mark.asyncio
async def test_activity_context_get_history_uses_current_channel_thread() -> None:
    graph = FakeGraph()
    activity = MessageActivity(
        id="reply-message-id",
        text="hello",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="channel"),
        reply_to_id="root-message-id",
        channel_data=ChannelData(
            team={"id": "team-thread-id", "aad_group_id": "team-group-id"},
            channel=ChannelInfo(id="channel-id"),
        ),
    )
    activity_sender = MagicMock()
    activity_sender.create_stream = MagicMock(return_value=MagicMock())

    ctx = ActivityContext(
        activity=activity,
        app_id="test-app-id",
        storage=MagicMock(),
        api=MagicMock(),
        user_token=None,
        conversation_ref=ConversationReference(
            bot=Account(id="bot-id"),
            conversation=ConversationAccount(id="conversation-id"),
            channel_id="msteams",
            service_url="https://service.example",
        ),
        is_signed_in=False,
        connection_name="graph",
        activity_sender=activity_sender,
        app_token=MagicMock(),
        cloud=PUBLIC,
    )
    ctx._app_graph = graph

    result = await ctx.get_history(2)

    assert result == ["channel-reply"]
    assert graph.teams.team_id == "team-group-id"
    assert graph.channels.channel_id == "channel-id"
    assert graph.channel_messages.thread_id == "root-message-id"


@pytest.mark.asyncio
async def test_activity_context_get_history_reads_thread_from_conversation_id() -> None:
    graph = FakeGraph()
    activity = MessageActivity(
        id="reply-message-id",
        text="hello",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(
            id="19:channel-id@thread.tacv2;messageid=root-message-id",
            conversation_type="channel",
        ),
        channel_data=ChannelData(
            team={"id": "team-thread-id", "aad_group_id": "team-group-id"},
            channel=ChannelInfo(id="channel-id"),
        ),
    )
    activity_sender = MagicMock()
    activity_sender.create_stream = MagicMock(return_value=MagicMock())

    ctx = ActivityContext(
        activity=activity,
        app_id="test-app-id",
        storage=MagicMock(),
        api=MagicMock(),
        user_token=None,
        conversation_ref=ConversationReference(
            bot=Account(id="bot-id"),
            conversation=ConversationAccount(id="19:channel-id@thread.tacv2;messageid=root-message-id"),
            channel_id="msteams",
            service_url="https://service.example",
        ),
        is_signed_in=False,
        connection_name="graph",
        activity_sender=activity_sender,
        app_token=MagicMock(),
        cloud=PUBLIC,
    )
    ctx._app_graph = graph

    result = await ctx.get_history(2)

    assert result == ["channel-reply"]
    assert graph.channel_messages.thread_id == "root-message-id"


@pytest.mark.asyncio
async def test_get_history_validates_count() -> None:
    app = App(**AppOptions(client_id="test-id", client_secret="test-secret"))

    with pytest.raises(ValueError, match="n must be greater than 0"):
        await app.get_history(n=0, chat_id="chat-id")


@pytest.mark.asyncio
async def test_get_history_requires_complete_channel_target() -> None:
    app = App(**AppOptions(client_id="test-id", client_secret="test-secret"))

    with pytest.raises(ValueError, match="team_aad_group_id and channel_id are required"):
        await app.get_history(n=1, channel_id="channel-id")


@pytest.mark.asyncio
async def test_activity_context_channel_history_requires_team_aad_group_id() -> None:
    activity = MessageActivity(
        id="reply-message-id",
        text="hello",
        from_=Account(id="user-id"),
        recipient=Account(id="bot-id"),
        conversation=ConversationAccount(id="conversation-id", conversation_type="channel"),
        channel_data=ChannelData(
            team={"id": "team-thread-id"},
            channel=ChannelInfo(id="channel-id"),
        ),
    )
    activity_sender = MagicMock()
    activity_sender.create_stream = MagicMock(return_value=MagicMock())
    ctx = ActivityContext(
        activity=activity,
        app_id="test-app-id",
        storage=MagicMock(),
        api=MagicMock(),
        user_token=None,
        conversation_ref=ConversationReference(
            bot=Account(id="bot-id"),
            conversation=ConversationAccount(id="conversation-id"),
            channel_id="msteams",
            service_url="https://service.example",
        ),
        is_signed_in=False,
        connection_name="graph",
        activity_sender=activity_sender,
        app_token=MagicMock(),
        cloud=PUBLIC,
    )
    ctx._app_graph = FakeGraph()

    with pytest.raises(ValueError, match="team_aad_group_id and channel_id are required"):
        await ctx.get_history(2)
