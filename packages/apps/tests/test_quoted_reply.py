"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft_teams.api import Account, MessageActivityInput, SentActivity
from microsoft_teams.api.models.entity import QuotedReplyEntity
from microsoft_teams.apps.routing.activity_context import ActivityContext


class TestActivityContextReply:
    """Tests for ActivityContext.reply() with quoted reply entity stamping."""

    def _create_activity_context(
        self,
        activity_id: str = "incoming-msg-123",
        activity_type: str = "message",
        activity_text: str = "Hello from user",
    ) -> ActivityContext[Any]:
        """Create an ActivityContext for testing with a mock activity sender."""
        mock_activity = MagicMock()
        mock_activity.id = activity_id
        mock_activity.type = activity_type
        mock_activity.text = activity_text
        mock_activity.from_ = Account(id="user-123", name="Test User")

        mock_activity_sender = MagicMock()
        mock_activity_sender.send = AsyncMock(
            return_value=SentActivity(
                id="sent-activity-id",
                activity_params=MessageActivityInput(text="sent"),
            )
        )
        mock_activity_sender.create_stream = MagicMock(return_value=MagicMock())

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
            activity_sender=mock_activity_sender,
            app_token=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_reply_stamps_quoted_reply_entity(self) -> None:
        """Test that reply() adds a QuotedReplyEntity to the activity."""
        ctx = self._create_activity_context(activity_id="msg-abc")
        await ctx.reply("Thanks!")

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 1
        entity = sent_activity.entities[0]
        assert isinstance(entity, QuotedReplyEntity)
        assert entity.quoted_reply.message_id == "msg-abc"

    @pytest.mark.asyncio
    async def test_reply_prepends_placeholder(self) -> None:
        """Test that reply() prepends the quoted placeholder to text."""
        ctx = self._create_activity_context(activity_id="msg-abc")
        await ctx.reply("Thanks!")

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-abc"/> Thanks!'

    @pytest.mark.asyncio
    async def test_reply_with_empty_text(self) -> None:
        """Test that reply() handles empty text correctly."""
        ctx = self._create_activity_context(activity_id="msg-abc")
        activity = MessageActivityInput(text="")
        await ctx.reply(activity)

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-abc"/>'

    @pytest.mark.asyncio
    async def test_reply_with_none_text(self) -> None:
        """Test that reply() handles None text correctly."""
        ctx = self._create_activity_context(activity_id="msg-abc")
        activity = MessageActivityInput()
        await ctx.reply(activity)

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-abc"/>'

    @pytest.mark.asyncio
    async def test_reply_with_no_activity_id(self) -> None:
        """Test that reply() does not stamp entity when activity.id is None."""
        ctx = self._create_activity_context(activity_id=None)
        await ctx.reply("Thanks!")

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == "Thanks!"
        assert sent_activity.entities is None

    @pytest.mark.asyncio
    async def test_reply_preserves_existing_entities(self) -> None:
        """Test that reply() preserves any pre-existing entities on the activity."""
        ctx = self._create_activity_context(activity_id="msg-abc")
        activity = MessageActivityInput(text="Hello")
        existing_entity = MagicMock()
        activity.entities = [existing_entity]

        await ctx.reply(activity)

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 2
        assert sent_activity.entities[0] is existing_entity
        assert isinstance(sent_activity.entities[1], QuotedReplyEntity)

    @pytest.mark.asyncio
    async def test_reply_with_activity_params(self) -> None:
        """Test that reply() works with an ActivityParams input."""
        ctx = self._create_activity_context(activity_id="msg-abc")
        activity = MessageActivityInput(text="Hello world")
        await ctx.reply(activity)

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-abc"/> Hello world'


class TestActivityContextQuoteReply:
    """Tests for ActivityContext.quote_reply() with arbitrary message ID."""

    def _create_activity_context(self) -> ActivityContext[Any]:
        """Create an ActivityContext for testing."""
        mock_activity = MagicMock()
        mock_activity.id = "incoming-msg-123"
        mock_activity.from_ = Account(id="user-123", name="Test User")

        mock_activity_sender = MagicMock()
        mock_activity_sender.send = AsyncMock(
            return_value=SentActivity(
                id="sent-activity-id",
                activity_params=MessageActivityInput(text="sent"),
            )
        )
        mock_activity_sender.create_stream = MagicMock(return_value=MagicMock())

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
            activity_sender=mock_activity_sender,
            app_token=MagicMock(),
        )

    @pytest.mark.asyncio
    async def test_quote_reply_stamps_entity_with_message_id(self) -> None:
        """Test that quote_reply() stamps entity with the provided message ID."""
        ctx = self._create_activity_context()
        await ctx.quote_reply("arbitrary-msg-id", "Quoting this!")

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 1
        entity = sent_activity.entities[0]
        assert isinstance(entity, QuotedReplyEntity)
        assert entity.quoted_reply.message_id == "arbitrary-msg-id"

    @pytest.mark.asyncio
    async def test_quote_reply_prepends_placeholder(self) -> None:
        """Test that quote_reply() prepends the quoted placeholder."""
        ctx = self._create_activity_context()
        await ctx.quote_reply("msg-xyz", "My reply text")

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-xyz"/> My reply text'

    @pytest.mark.asyncio
    async def test_quote_reply_with_empty_text(self) -> None:
        """Test that quote_reply() handles empty text correctly."""
        ctx = self._create_activity_context()
        activity = MessageActivityInput(text="")
        await ctx.quote_reply("msg-xyz", activity)

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-xyz"/>'

    @pytest.mark.asyncio
    async def test_quote_reply_with_activity_params(self) -> None:
        """Test that quote_reply() works with an ActivityParams input."""
        ctx = self._create_activity_context()
        activity = MessageActivityInput(text="Hello world")
        await ctx.quote_reply("msg-xyz", activity)

        sent_activity = ctx._activity_sender.send.call_args[0][0]
        assert sent_activity.text == '<quoted messageId="msg-xyz"/> Hello world'
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 1
        assert isinstance(sent_activity.entities[0], QuotedReplyEntity)
