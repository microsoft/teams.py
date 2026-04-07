"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from unittest.mock import MagicMock

import pytest
from microsoft_teams.api import (
    Account,
    ConversationAccount,
    MessageFetchTaskActionValue,
    MessageFetchTaskData,
    MessageFetchTaskInvokeActivity,
    MessageFetchTaskInvokeValue,
    TaskFetchInvokeActivity,
    TaskModuleInvokeResponse,
    TaskModuleMessageResponse,
    TaskModuleRequest,
)
from microsoft_teams.apps import ActivityContext, App


class TestFeedbackRouting:
    """Test cases for custom feedback routing functionality."""

    @pytest.fixture
    def app(self):
        return App(storage=MagicMock(), client_id="test-client-id", client_secret="test-secret")

    @pytest.fixture
    def fetch_task_activity(self):
        return MessageFetchTaskInvokeActivity(
            id="activity-1",
            type="invoke",
            name="message/fetchTask",
            from_=Account(id="user-1", name="User"),
            recipient=Account(id="bot-1", name="Bot"),
            conversation=ConversationAccount(id="conv-1", conversation_type="personal"),
            channel_id="msteams",
            value=MessageFetchTaskInvokeValue(
                data=MessageFetchTaskData(action_value=MessageFetchTaskActionValue(reaction="like"))
            ),
        )

    def test_on_message_fetch_task_registers_handler(
        self, app: App, fetch_task_activity: MessageFetchTaskInvokeActivity
    ) -> None:
        @app.on_message_fetch_task
        async def handler(ctx: ActivityContext[MessageFetchTaskInvokeActivity]) -> TaskModuleInvokeResponse:
            return TaskModuleInvokeResponse(task=TaskModuleMessageResponse(value="feedback form"))

        handlers = app.router.select_handlers(fetch_task_activity)
        assert len(handlers) == 1
        assert handlers[0] == handler

    def test_on_message_fetch_task_does_not_match_other_invokes(self, app: App) -> None:
        @app.on_message_fetch_task
        async def handler(ctx: ActivityContext[MessageFetchTaskInvokeActivity]) -> TaskModuleInvokeResponse:
            return TaskModuleInvokeResponse(task=TaskModuleMessageResponse(value="feedback form"))

        other_activity = TaskFetchInvokeActivity(
            id="activity-2",
            type="invoke",
            name="task/fetch",
            from_=Account(id="user-1", name="User"),
            recipient=Account(id="bot-1", name="Bot"),
            conversation=ConversationAccount(id="conv-1", conversation_type="personal"),
            channel_id="msteams",
            value=TaskModuleRequest(data={}),
        )

        handlers = app.router.select_handlers(other_activity)
        assert len(handlers) == 0

    def test_on_message_fetch_task_reaction_dislike(self, app: App) -> None:
        @app.on_message_fetch_task
        async def handler(ctx: ActivityContext[MessageFetchTaskInvokeActivity]) -> TaskModuleInvokeResponse:
            return TaskModuleInvokeResponse(task=TaskModuleMessageResponse(value="feedback form"))

        dislike_activity = MessageFetchTaskInvokeActivity(
            id="activity-3",
            type="invoke",
            name="message/fetchTask",
            from_=Account(id="user-1", name="User"),
            recipient=Account(id="bot-1", name="Bot"),
            conversation=ConversationAccount(id="conv-1", conversation_type="personal"),
            channel_id="msteams",
            value=MessageFetchTaskInvokeValue(
                data=MessageFetchTaskData(action_value=MessageFetchTaskActionValue(reaction="dislike"))
            ),
        )

        handlers = app.router.select_handlers(dislike_activity)
        assert len(handlers) == 1
        assert handlers[0] == handler
