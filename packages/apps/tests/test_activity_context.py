"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.api import Account, MessageActivityInput, SentActivity
from microsoft_teams.apps.routing.activity_context import ActivityContext


class TestActivityContextSendTargeted:
    """Tests for ActivityContext.send() with targeted message recipient inference."""

    def _create_activity_context(
        self,
        from_account: Account,
    ) -> ActivityContext[Any]:
        """Create an ActivityContext for testing with a mock sender."""
        mock_activity = MagicMock()
        mock_activity.from_ = from_account

        mock_sender = MagicMock()
        mock_sender.send = AsyncMock(
            return_value=SentActivity(
                id="sent-activity-id",
                activity_params=MessageActivityInput(text="sent"),
            )
        )
        mock_sender.create_stream = MagicMock(return_value=MagicMock())

        mock_conversation_ref = MagicMock()

        return ActivityContext(
            activity=mock_activity,
            app_id="test-app-id",
            logger=MagicMock(),
            storage=MagicMock(),
            api=MagicMock(),
            user_token=None,
            conversation_ref=mock_conversation_ref,
            is_signed_in=False,
            connection_name="test-connection",
            sender=mock_sender,
            app_token=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_targeted_create_sets_recipient_to_incoming_sender(self) -> None:
        """
        When sending a targeted message (is_targeted=True, no id), the recipient
        should be set to the incoming activity's sender (from_).
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message without recipient or id (this is a create)
        activity = MessageActivityInput(text="Hello").with_targeted_recipient(True)
        assert activity.recipient is None  # Initially no recipient
        assert activity.id is None  # No id means create, not update

        await ctx.send(activity)

        # Verify send was called
        ctx._plugin.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = ctx._plugin.send.call_args[0][0]

        # Verify recipient was set to the incoming sender
        assert sent_activity.recipient == incoming_sender

    @pytest.mark.asyncio
    async def test_targeted_update_does_not_modify_recipient(self) -> None:
        """
        When updating a targeted message (is_targeted=True, id is set), the recipient
        should not be modified because recipient cannot be changed on updates.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message update (has id set)
        activity = MessageActivityInput(text="Updated text").with_targeted_recipient(True)
        activity.id = "existing-activity-id"  # This makes it an update
        assert activity.recipient is None

        await ctx.send(activity)

        # Verify send was called
        ctx._plugin.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = ctx._plugin.send.call_args[0][0]

        # Verify recipient was NOT set for updates
        assert sent_activity.recipient is None

    @pytest.mark.asyncio
    async def test_targeted_create_does_not_override_explicit_recipient(self) -> None:
        """
        When sending a targeted message with an explicit recipient already set,
        the recipient should not be overridden.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        explicit_recipient = Account(id="other-user-456", name="Other User")
        ctx = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message with explicit recipient
        activity = MessageActivityInput(text="Hello").with_targeted_recipient(explicit_recipient.id)
        assert activity.recipient is not None  # Recipient was set by with_targeted_recipient

        await ctx.send(activity)

        # Verify send was called
        ctx._plugin.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = ctx._plugin.send.call_args[0][0]

        # Verify recipient was NOT overridden - should still be the explicit recipient
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == explicit_recipient.id

    @pytest.mark.asyncio
    async def test_non_targeted_message_does_not_set_recipient(self) -> None:
        """
        When sending a non-targeted message, the recipient should not be set.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx = self._create_activity_context(from_account=incoming_sender)

        # Create a regular (non-targeted) message
        activity = MessageActivityInput(text="Hello")
        assert activity.is_targeted is None
        assert activity.recipient is None

        await ctx.send(activity)

        # Verify send was called
        ctx._plugin.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = ctx._plugin.send.call_args[0][0]

        # Verify recipient was NOT set for non-targeted messages
        assert sent_activity.recipient is None
