"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.api import ApiClient
from microsoft_teams.api.activities.message.message import MessageActivityInput
from microsoft_teams.api.models.conversation.conversation_reference import ConversationReference
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
        mock_conversations.members_client.get_by_id = AsyncMock(return_value=True)

        api.conversations = mock_conversations
        return api

    @pytest.fixture
    def mock_http(self):
        """Create a mock HttpPlugin."""
        http = MagicMock()
        http.send = AsyncMock()
        http.send.return_value = "sent-activity"
        return http

    @pytest.fixture
    def mock_logger(self):
        """Create a mock Logger."""
        return MagicMock()

    @pytest.fixture
    def function_context(self, mock_api: ApiClient, mock_http: Any, mock_logger: Any) -> FunctionContext[Any]:
        ctx: FunctionContext[Any] = FunctionContext(
            id="bot-123",
            name="Test Bot",
            api=mock_api,
            http=mock_http,
            log=mock_logger,
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
        mock_http: Any,
    ) -> None:
        """Test sending a string message."""

        result = await function_context.send("Hello world")
        assert result == "sent-activity"

        sent_activity, conversation_ref, is_targeted = mock_http.send.call_args[0]

        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.text == "Hello world"

        assert isinstance(conversation_ref, ConversationReference)
        assert conversation_ref.conversation.id == "conv-123"
        assert is_targeted is False

    async def test_send_adaptive_card(
        self,
        function_context: FunctionContext[Any],
        mock_http: Any,
    ) -> None:
        """Test sending an AdaptiveCard message."""

        card = AdaptiveCard(schema="1.0")
        result = await function_context.send(card)
        assert result == "sent-activity"

        sent_activity, conversation_ref, is_targeted = mock_http.send.call_args[0]

        assert sent_activity.attachments[0].content == card
        assert conversation_ref.conversation.id == "conv-123"
        assert is_targeted is False

    async def test_send_creates_conversation_if_none(
        self, function_context: FunctionContext[Any], mock_http: Any
    ) -> None:
        """Test send() creates a conversation when _resolved_conversation_id is None."""

        function_context.chat_id = None

        mock_http.send.return_value = "sent-new-conv"

        result = await function_context.send("Hello new conversation")

        assert result == "sent-new-conv"
        # Ensure conversation was created
        assert function_context.api.conversations.create.call_count == 1  # type: ignore
        sent_activity, conversation_ref, is_targeted = mock_http.send.call_args[0]
        assert sent_activity.text == "Hello new conversation"
        assert conversation_ref.conversation.id == "new-conv"
        assert is_targeted is False

    async def test_send_with_targeted_recipient_id(
        self,
        function_context: FunctionContext[Any],
        mock_http: Any,
    ) -> None:
        """Test sending a targeted message sets recipient and is_targeted flag."""

        result = await function_context.send("Private message", targeted_recipient_id="user-123")
        assert result == "sent-activity"

        sent_activity, conversation_ref, is_targeted = mock_http.send.call_args[0]

        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.text == "Private message"
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == "user-123"
        assert is_targeted is True

    async def test_send_without_targeted_recipient_id(
        self,
        function_context: FunctionContext[Any],
        mock_http: Any,
    ) -> None:
        """Test sending a non-targeted message does not set recipient."""

        result = await function_context.send("Public message")
        assert result == "sent-activity"

        sent_activity, conversation_ref, is_targeted = mock_http.send.call_args[0]

        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.text == "Public message"
        assert sent_activity.recipient is None
        assert is_targeted is False
