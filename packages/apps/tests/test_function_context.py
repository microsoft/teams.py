"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.api import ApiClient, SentActivity
from microsoft_teams.api.activities.message.message import MessageActivityInput
from microsoft_teams.apps import FunctionContext
from microsoft_teams.cards import AdaptiveCard


@pytest.mark.asyncio
class TestFunctionContextSend:
    """Test cases for FunctionContext."""

    @pytest.fixture
    def mock_api(self):
        """Create a mock ApiClient."""
        api = MagicMock(spec=ApiClient)
        api.service_url = "https://test.service.url"
        mock_conversations = MagicMock()
        mock_conversations.create = AsyncMock(return_value=MagicMock(id="new-conv"))
        mock_conversations.get_member_by_id = AsyncMock(return_value=True)
        mock_activities = MagicMock()
        mock_activities.create = AsyncMock(
            return_value=SentActivity(id="sent-activity", activity_params=MessageActivityInput(text="sent"))
        )
        mock_activities.update = AsyncMock(
            return_value=SentActivity(id="updated-activity", activity_params=MessageActivityInput(text="updated"))
        )
        mock_conversations.activities.return_value = mock_activities

        async def create_activity(conversation_id: str, activity: Any) -> SentActivity:
            mock_conversations.activities(conversation_id)
            return await mock_activities.create(activity)

        async def update_activity(conversation_id: str, activity_id: str, activity: Any) -> SentActivity:
            mock_conversations.activities(conversation_id)
            return await mock_activities.update(activity_id, activity)

        mock_conversations.create_activity = AsyncMock(side_effect=create_activity)
        mock_conversations.update_activity = AsyncMock(side_effect=update_activity)

        api.conversations = mock_conversations
        api.clone.return_value = api
        return api

    @pytest.fixture
    def mock_logger(self):
        """Create a mock Logger."""
        return MagicMock()

    @pytest.fixture
    def function_context(self, mock_api: ApiClient) -> FunctionContext[Any]:
        ctx: FunctionContext[Any] = FunctionContext(
            id="bot-123",
            name="Test Bot",
            api=mock_api,
            data={"some": "payload"},
            app_session_id="dummy-session",
            tenant_id="tenant-789",
            user_id="user-456",
            user_name="Test User",
            page_id="page-001",
            auth_token="token-abc",
            chat_id="conv-123",
        )
        return ctx

    async def test_send_string_activity(
        self,
        function_context: FunctionContext[Any],
    ) -> None:
        """Test sending a string message."""

        result = await function_context.send("Hello world")
        assert result is not None
        assert result.id == "sent-activity"

        sent_activity = function_context.api.conversations.activities.return_value.create.call_args[0][0]

        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.text == "Hello world"
        assert sent_activity.from_.id == "bot-123"
        assert sent_activity.conversation.id == "conv-123"
        function_context.api.conversations.activities.assert_called_once_with("conv-123")

    async def test_send_adaptive_card(
        self,
        function_context: FunctionContext[Any],
    ) -> None:
        """Test sending an AdaptiveCard message."""

        card = AdaptiveCard(schema="1.0")
        result = await function_context.send(card)
        assert result is not None
        assert result.id == "sent-activity"

        sent_activity = function_context.api.conversations.activities.return_value.create.call_args[0][0]

        assert sent_activity.attachments[0].content == card
        function_context.api.conversations.activities.assert_called_once_with("conv-123")

    async def test_send_creates_conversation_if_none(self, function_context: FunctionContext[Any]) -> None:
        """Test send() creates a conversation when _resolved_conversation_id is None."""

        function_context.chat_id = None

        function_context.api.conversations.activities.return_value.create.return_value = SentActivity(
            id="sent-new-conv", activity_params=MessageActivityInput(text="sent")
        )

        result = await function_context.send("Hello new conversation")

        assert result is not None
        assert result.id == "sent-new-conv"
        # Ensure conversation was created
        assert function_context.api.conversations.create.call_count == 1  # type: ignore
        sent_activity = function_context.api.conversations.activities.return_value.create.call_args[0][0]
        assert sent_activity.text == "Hello new conversation"
        function_context.api.conversations.activities.assert_called_with("new-conv")

    async def test_send_existing_activity_updates(self, function_context: FunctionContext[Any]) -> None:
        activity = MessageActivityInput(text="Updated message")
        activity.id = "existing-msg-id"

        result = await function_context.send(activity)

        assert result is not None
        assert result.id == "updated-activity"
        function_context.api.conversations.activities.return_value.update.assert_called_once_with(
            "existing-msg-id",
            activity,
        )
        function_context.api.conversations.activities.return_value.create.assert_not_called()
