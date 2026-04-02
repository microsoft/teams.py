"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import Account, MessageActivityInput, SentActivity
from microsoft_teams.apps.routing.activity_context import ActivityContext


def _create_activity_context(
    is_signed_in: bool = False,
    user_token: str | None = None,
    activity: Any = None,
) -> tuple[ActivityContext[Any], MagicMock]:
    mock_activity = activity if activity is not None else MagicMock()

    mock_activity_sender = MagicMock()
    mock_activity_sender.send = AsyncMock(
        return_value=SentActivity(
            id="sent-activity-id",
            activity_params=MessageActivityInput(text="sent"),
        )
    )
    mock_activity_sender.create_stream = MagicMock(return_value=MagicMock())

    ctx = ActivityContext(
        activity=mock_activity,
        app_id="test-app-id",
        storage=MagicMock(),
        api=MagicMock(),
        user_token=user_token,
        conversation_ref=MagicMock(),
        is_signed_in=is_signed_in,
        connection_name="test-connection",
        activity_sender=mock_activity_sender,
        app_token=MagicMock(),
    )
    return ctx, mock_activity_sender


class TestActivityContextSendTargeted:
    """Tests for ActivityContext.send() with targeted message recipient inference."""

    def _create_activity_context(self, from_account: Account) -> tuple[ActivityContext[Any], MagicMock]:
        """Create an ActivityContext for testing with a mock activity sender."""
        mock_activity = MagicMock()
        mock_activity.from_ = from_account
        return _create_activity_context(activity=mock_activity)

    @pytest.mark.asyncio
    async def test_targeted_message_with_explicit_recipient(self) -> None:
        """
        When sending a targeted message with an explicit recipient set,
        the recipient should be passed through correctly.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message with recipient explicitly set
        activity = MessageActivityInput(text="Hello").with_recipient(incoming_sender, is_targeted=True)
        assert activity.recipient is not None
        assert activity.id is None  # No id means create, not update

        await ctx.send(activity)

        # Verify send was called
        mock_sender.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = mock_sender.send.call_args[0][0]

        # Verify recipient was preserved
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == incoming_sender.id
        assert sent_activity.recipient.name == incoming_sender.name
        assert sent_activity.recipient.is_targeted is True

    @pytest.mark.asyncio
    async def test_targeted_update_preserves_recipient(self) -> None:
        """
        When updating a targeted message, the recipient should be preserved.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message update (has id set)
        activity = MessageActivityInput(text="Updated text").with_recipient(incoming_sender, is_targeted=True)
        activity.id = "existing-activity-id"  # This makes it an update

        await ctx.send(activity)

        # Verify send was called
        mock_sender.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = mock_sender.send.call_args[0][0]

        # Verify recipient was preserved
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == incoming_sender.id
        assert sent_activity.recipient.name == incoming_sender.name
        assert sent_activity.recipient.is_targeted is True

    @pytest.mark.asyncio
    async def test_targeted_with_different_recipient(self) -> None:
        """
        When sending a targeted message with a different recipient,
        the recipient should not be overridden.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        explicit_recipient = Account(id="other-user-456", name="Other User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message with explicit recipient
        activity = MessageActivityInput(text="Hello").with_recipient(explicit_recipient, is_targeted=True)
        assert activity.recipient is not None

        await ctx.send(activity)

        # Verify send was called
        mock_sender.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = mock_sender.send.call_args[0][0]

        # Verify recipient was preserved
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == explicit_recipient.id

    @pytest.mark.asyncio
    async def test_non_targeted_message_does_not_set_recipient(self) -> None:
        """
        When sending a non-targeted message, the recipient should not be set.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)

        # Create a regular (non-targeted) message
        activity = MessageActivityInput(text="Hello")
        assert activity.recipient is None

        await ctx.send(activity)

        # Verify send was called
        mock_sender.send.assert_called_once()

        # Get the activity that was passed to send
        sent_activity = mock_sender.send.call_args[0][0]

        # Verify recipient was NOT set for non-targeted messages
        assert sent_activity.recipient is None


class TestActivityContextSend:
    """Tests for ActivityContext.send() with string and AdaptiveCard inputs."""

    @pytest.mark.asyncio
    async def test_send_with_string_message(self) -> None:
        """Sending a plain string wraps it in a MessageActivityInput."""
        ctx, mock_sender = _create_activity_context()

        result = await ctx.send("Hello, world!")

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.text == "Hello, world!"
        assert isinstance(result, SentActivity)

    @pytest.mark.asyncio
    async def test_send_with_adaptive_card(self) -> None:
        """Sending an AdaptiveCard wraps it via add_card."""
        from microsoft_teams.cards import AdaptiveCard

        ctx, mock_sender = _create_activity_context()
        card = AdaptiveCard()

        result = await ctx.send(card)

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert isinstance(sent_activity, MessageActivityInput)
        # The card should have been attached
        assert sent_activity.attachments is not None
        assert len(sent_activity.attachments) > 0
        assert isinstance(result, SentActivity)


class TestActivityContextReply:
    """Tests for ActivityContext.reply()."""

    @pytest.mark.asyncio
    async def test_reply_with_string(self) -> None:
        """reply() with a plain string sends a message with reply_to_id set."""
        mock_activity = MagicMock()
        mock_activity.type = "message"
        mock_activity.id = "original-id"
        mock_activity.text = "Original message"
        mock_activity.from_ = MagicMock()
        mock_activity.from_.id = "user-1"
        mock_activity.from_.name = "User One"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)

        await ctx.reply("My reply")

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.reply_to_id == "original-id"
        assert "My reply" in (sent_activity.text or "")

    @pytest.mark.asyncio
    async def test_reply_with_activity_params(self) -> None:
        """reply() with an ActivityParams instance sets reply_to_id and delegates to send."""
        mock_activity = MagicMock()
        mock_activity.type = "event"
        mock_activity.id = "evt-id-999"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)

        params = MessageActivityInput(text="Params reply")
        await ctx.reply(params)

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert sent_activity.reply_to_id == "evt-id-999"


class TestActivityContextBuildBlockQuote:
    """Tests for ActivityContext._build_block_quote_for_activity()."""

    def _make_message_activity(self, text: str, activity_id: str = "act-1") -> MagicMock:
        mock_activity = MagicMock()
        mock_activity.type = "message"
        mock_activity.id = activity_id
        mock_activity.text = text
        mock_activity.from_ = MagicMock()
        mock_activity.from_.id = "user-xyz"
        mock_activity.from_.name = "Test User"
        return mock_activity

    def test_message_activity_returns_html_blockquote(self) -> None:
        """Activity type 'message' with text produces a blockquote HTML string."""
        activity = self._make_message_activity("Hello blockquote")
        ctx, _ = _create_activity_context(activity=activity)

        result = ctx._build_block_quote_for_activity()

        assert result is not None
        assert "<blockquote" in result
        assert "Hello blockquote" in result
        assert "Test User" in result
        assert "act-1" in result

    def test_long_text_is_truncated(self) -> None:
        """Text longer than 120 characters is truncated with an ellipsis."""
        long_text = "A" * 130
        activity = self._make_message_activity(long_text)
        ctx, _ = _create_activity_context(activity=activity)

        result = ctx._build_block_quote_for_activity()

        assert result is not None
        # Truncated text should be 120 chars + "..."
        assert "A" * 120 + "..." in result
        # The full text should not be present
        assert long_text not in result

    def test_non_message_activity_returns_none(self) -> None:
        """Activity type other than 'message' returns None."""
        mock_activity = MagicMock()
        mock_activity.type = "event"
        ctx, _ = _create_activity_context(activity=mock_activity)

        result = ctx._build_block_quote_for_activity()

        assert result is None


class TestActivityContextUserGraph:
    """Tests for ActivityContext.user_graph property."""

    def test_user_graph_raises_when_not_signed_in(self) -> None:
        """user_graph raises ValueError when is_signed_in is False."""
        ctx, _ = _create_activity_context(is_signed_in=False, user_token="some.jwt.token")

        with pytest.raises(ValueError, match="signed in"):
            _ = ctx.user_graph

    def test_user_graph_raises_when_no_user_token(self) -> None:
        """user_graph raises ValueError when is_signed_in is True but user_token is None."""
        ctx, _ = _create_activity_context(is_signed_in=True, user_token=None)

        with pytest.raises(ValueError, match="No user token"):
            _ = ctx.user_graph

    def test_user_graph_raises_runtime_error_when_graph_import_fails(self) -> None:
        """user_graph raises RuntimeError when _get_graph_client raises ImportError."""
        ctx, _ = _create_activity_context(is_signed_in=True, user_token="some.jwt.token")

        with patch(
            "microsoft_teams.apps.routing.activity_context._get_graph_client",
            side_effect=ImportError("graph not installed"),
        ):
            with pytest.raises(RuntimeError, match="Failed to create user graph client"):
                _ = ctx.user_graph


class TestActivityContextAppGraph:
    """Tests for ActivityContext.app_graph property."""

    def test_app_graph_raises_runtime_error_when_graph_import_fails(self) -> None:
        """app_graph raises RuntimeError when _get_graph_client raises ImportError."""
        ctx, _ = _create_activity_context()

        with patch(
            "microsoft_teams.apps.routing.activity_context._get_graph_client",
            side_effect=ImportError("graph not installed"),
        ):
            with pytest.raises(RuntimeError, match="Failed to create app graph client"):
                _ = ctx.app_graph

    def test_app_graph_returns_cached_client_on_second_access(self) -> None:
        """app_graph returns the same instance on repeated access (lazy-cached)."""
        mock_graph_client = MagicMock()
        ctx, _ = _create_activity_context()

        with patch(
            "microsoft_teams.apps.routing.activity_context._get_graph_client",
            return_value=mock_graph_client,
        ):
            first = ctx.app_graph
            second = ctx.app_graph

        assert first is second
        # _get_graph_client should only have been called once (caching)
        assert ctx._app_graph is mock_graph_client


class TestActivityContextSignIn:
    """Tests for ActivityContext.sign_in()."""

    @pytest.mark.asyncio
    async def test_sign_in_returns_token_when_already_available(self) -> None:
        """sign_in returns the existing token when the API call succeeds."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-001"
        mock_activity.conversation.is_group = False

        ctx, _ = _create_activity_context(activity=mock_activity)

        token_response = MagicMock()
        token_response.token = "existing-token-value"
        ctx.api.users.token.get = AsyncMock(return_value=token_response)

        result = await ctx.sign_in()

        assert result == "existing-token-value"
        ctx.api.users.token.get.assert_called_once()


class TestActivityContextSignOut:
    """Tests for ActivityContext.sign_out()."""

    @pytest.mark.asyncio
    async def test_sign_out_logs_error_and_does_not_raise_on_failure(self) -> None:
        """sign_out logs the error but does not propagate exceptions."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-003"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.token.sign_out = AsyncMock(side_effect=Exception("API failure"))

        with patch.object(ctx.logger, "error") as mock_log_error:
            # Should not raise
            await ctx.sign_out()

            mock_log_error.assert_called_once()
            logged_message = mock_log_error.call_args[0][0]
            assert "Failed to sign out user" in logged_message
