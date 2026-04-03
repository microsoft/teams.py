"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import (
    Account,
    ConversationAccount,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
)
from microsoft_teams.apps.activity_sender import ActivitySender


class TestActivitySender:
    """Test cases for ActivitySender."""

    @pytest.fixture
    def sender(self):
        """Create an ActivitySender for testing."""
        mock_client = MagicMock()
        return ActivitySender(client=mock_client)

    @pytest.fixture
    def conversation_ref(self):
        """Create a conversation reference for testing."""
        return ConversationReference(
            bot=Account(id="bot-123", name="Test Bot", role="bot"),
            conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
            channel_id="msteams",
            service_url="https://test.service.url",
        )

    def _create_sent_activity(self, activity, activity_id="msg-123"):
        """Helper to create a proper SentActivity mock."""
        return SentActivity(id=activity_id, activity_params=activity)

    @pytest.mark.asyncio
    async def test_send_new_message_calls_create(self, sender, conversation_ref):
        """Test that new messages (no id) use the create method."""
        activity = MessageActivityInput(text="Hello")

        mock_activities = MagicMock()
        mock_activities.create = AsyncMock(return_value=self._create_sent_activity(activity))

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            mock_activities.create.assert_called_once_with(activity)

    @pytest.mark.asyncio
    async def test_send_existing_message_calls_update(self, sender, conversation_ref):
        """Test that messages with an id use the update method."""
        activity = MessageActivityInput(text="Updated message")
        activity.id = "existing-msg-id"

        mock_activities = MagicMock()
        mock_activities.update = AsyncMock(return_value=self._create_sent_activity(activity, "existing-msg-id"))

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            mock_activities.update.assert_called_once_with("existing-msg-id", activity)

    @pytest.mark.asyncio
    async def test_send_sets_from_and_conversation(self, sender, conversation_ref):
        """Test that send merges activity with conversation reference."""
        activity = MessageActivityInput(text="Hello")

        mock_activities = MagicMock()
        mock_activities.create = AsyncMock(return_value=self._create_sent_activity(activity))

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            assert activity.from_ == conversation_ref.bot
            assert activity.conversation == conversation_ref.conversation

    @pytest.mark.asyncio
    async def test_send_targeted_message_calls_create_targeted(self, sender, conversation_ref):
        """Test that targeted messages use the create_targeted method."""
        recipient = Account(id="user-123", name="Test User", role="user")
        activity = MessageActivityInput(text="Hello").with_recipient(recipient, is_targeted=True)

        mock_activities = MagicMock()
        mock_activities.create_targeted = AsyncMock(return_value=self._create_sent_activity(activity))

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            mock_activities.create_targeted.assert_called_once_with(activity)
            mock_activities.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_non_targeted_message_does_not_call_create_targeted(self, sender, conversation_ref):
        """Test that non-targeted messages use the regular create method."""
        activity = MessageActivityInput(text="Hello")

        mock_activities = MagicMock()
        mock_activities.create = AsyncMock(return_value=self._create_sent_activity(activity))

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            mock_activities.create.assert_called_once_with(activity)
            mock_activities.create_targeted.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_targeted_message_calls_update_targeted(self, sender, conversation_ref):
        """Test that targeted message updates use the update_targeted method."""
        activity = MessageActivityInput(text="Updated targeted message")
        activity.recipient = Account(id="user-123", name="Test User", role="user", is_targeted=True)
        activity.id = "existing-msg-id"

        mock_activities = MagicMock()
        mock_activities.update_targeted = AsyncMock(
            return_value=self._create_sent_activity(activity, "existing-msg-id")
        )

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            mock_activities.update_targeted.assert_called_once_with("existing-msg-id", activity)
            mock_activities.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_non_targeted_message_calls_update(self, sender, conversation_ref):
        """Test that non-targeted message updates use the regular update method."""
        activity = MessageActivityInput(text="Updated message")
        activity.id = "existing-msg-id"

        mock_activities = MagicMock()
        mock_activities.update = AsyncMock(return_value=self._create_sent_activity(activity, "existing-msg-id"))

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.send(activity, conversation_ref)

            mock_activities.update.assert_called_once_with("existing-msg-id", activity)
            mock_activities.update_targeted.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_calls_delete(self, sender, conversation_ref):
        """Test that delete() calls the underlying delete method."""
        mock_activities = MagicMock()
        mock_activities.delete = AsyncMock(return_value=None)

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.delete("msg-123", conversation_ref)

            mock_activities.delete.assert_called_once_with("msg-123")
            mock_activities.delete_targeted.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_targeted_calls_delete_targeted(self, sender, conversation_ref):
        """Test that delete() with targeted=True calls delete_targeted."""
        mock_activities = MagicMock()
        mock_activities.delete_targeted = AsyncMock(return_value=None)

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.delete("msg-123", conversation_ref, targeted=True)

            mock_activities.delete_targeted.assert_called_once_with("msg-123")
            mock_activities.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_uses_correct_conversation_id(self, sender, conversation_ref):
        """Test that delete() uses conversation id from ref."""
        mock_activities = MagicMock()
        mock_activities.delete = AsyncMock(return_value=None)

        with patch("microsoft_teams.apps.activity_sender.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await sender.delete("msg-123", conversation_ref)

            mock_api.conversations.activities.assert_called_once_with(conversation_ref.conversation.id)
