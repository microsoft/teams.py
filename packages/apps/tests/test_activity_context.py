"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import Account, MessageActivityInput, SentActivity
from microsoft_teams.api.auth.cloud_environment import PUBLIC
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
        cloud=PUBLIC,
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
        """reply() with a plain string stamps a quotedReply entity and placeholder."""
        from microsoft_teams.api.models.entity import QuotedReplyEntity

        mock_activity = MagicMock()
        mock_activity.type = "message"
        mock_activity.id = "original-id"
        mock_activity.text = "Original message"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)

        await ctx.reply("My reply")

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 1
        assert isinstance(sent_activity.entities[0], QuotedReplyEntity)
        assert sent_activity.entities[0].quoted_reply.message_id == "original-id"
        assert '<quoted messageId="original-id"/>' in (sent_activity.text or "")
        assert "My reply" in (sent_activity.text or "")

    @pytest.mark.asyncio
    async def test_reply_with_activity_params(self) -> None:
        """reply() with a MessageActivityInput stamps a quotedReply entity."""
        from microsoft_teams.api.models.entity import QuotedReplyEntity

        mock_activity = MagicMock()
        mock_activity.type = "message"
        mock_activity.id = "evt-id-999"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)

        params = MessageActivityInput(text="Params reply")
        await ctx.reply(params)

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert sent_activity.entities is not None
        assert isinstance(sent_activity.entities[0], QuotedReplyEntity)
        assert sent_activity.entities[0].quoted_reply.message_id == "evt-id-999"


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
        """user_graph raises RuntimeError when create_graph_client raises ImportError."""
        ctx, _ = _create_activity_context(is_signed_in=True, user_token="some.jwt.token")

        with patch(
            "microsoft_teams.apps.routing.activity_context.create_graph_client",
            side_effect=ImportError("graph not installed"),
        ):
            with pytest.raises(RuntimeError, match="Failed to create user graph client"):
                _ = ctx.user_graph

    def test_user_graph_returns_client_when_signed_in_with_token(self) -> None:
        """user_graph returns the created Graph client on success."""
        mock_graph_client = MagicMock()
        ctx, _ = _create_activity_context(is_signed_in=True, user_token="header.payload.sig")

        with (
            patch("microsoft_teams.apps.routing.activity_context.JsonWebToken", return_value=MagicMock()),
            patch(
                "microsoft_teams.apps.routing.activity_context.create_graph_client",
                return_value=mock_graph_client,
            ),
        ):
            assert ctx.user_graph is mock_graph_client

    def test_user_graph_returns_cached_client_on_second_access(self) -> None:
        """user_graph caches the client on first call (lazy initialization)."""
        mock_graph_client = MagicMock()
        ctx, _ = _create_activity_context(is_signed_in=True, user_token="header.payload.sig")

        with (
            patch("microsoft_teams.apps.routing.activity_context.JsonWebToken", return_value=MagicMock()),
            patch(
                "microsoft_teams.apps.routing.activity_context.create_graph_client",
                return_value=mock_graph_client,
            ) as mock_factory,
        ):
            first = ctx.user_graph
            second = ctx.user_graph

        assert first is second
        mock_factory.assert_called_once()

    def test_user_graph_re_raises_import_error_without_wrapping(self) -> None:
        """user_graph re-raises ImportError directly (does not wrap in RuntimeError)."""
        ctx, _ = _create_activity_context(is_signed_in=True, user_token="header.payload.sig")

        with (
            patch("microsoft_teams.apps.routing.activity_context.JsonWebToken", return_value=MagicMock()),
            patch(
                "microsoft_teams.apps.routing.activity_context.create_graph_client",
                side_effect=ImportError("graph not installed"),
            ),
        ):
            with pytest.raises(ImportError, match="graph not installed"):
                _ = ctx.user_graph


class TestActivityContextAppGraph:
    """Tests for ActivityContext.app_graph property."""

    def test_app_graph_raises_import_error_when_graph_not_installed(self) -> None:
        """app_graph raises ImportError when graph dependencies are not installed."""
        ctx, _ = _create_activity_context()

        with patch(
            "microsoft_teams.apps.routing.activity_context.create_graph_client",
            side_effect=ImportError("graph not installed"),
        ):
            with pytest.raises(ImportError, match="graph not installed"):
                _ = ctx.app_graph

    def test_app_graph_returns_cached_client_on_second_access(self) -> None:
        """app_graph returns the same instance on repeated access (lazy-cached)."""
        mock_graph_client = MagicMock()
        ctx, _ = _create_activity_context()

        with patch(
            "microsoft_teams.apps.routing.activity_context.create_graph_client",
            return_value=mock_graph_client,
        ):
            first = ctx.app_graph
            second = ctx.app_graph

        assert first is second
        # create_graph_client should only have been called once (caching)
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

    @pytest.mark.asyncio
    async def test_sign_in_sends_oauth_card_when_no_existing_token(self) -> None:
        """sign_in falls through to OAuth card flow when token API fails, returns None."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-001"
        mock_activity.conversation.is_group = False

        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        ctx.api.users.token.get = AsyncMock(side_effect=Exception("no token"))

        resource_response = MagicMock()
        resource_response.token_exchange_resource = MagicMock()
        resource_response.token_post_resource = MagicMock()
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api.bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.MessageActivityInput"),
            patch("microsoft_teams.apps.routing.activity_context.card_attachment"),
            patch("microsoft_teams.apps.routing.activity_context.OAuthCardAttachment"),
            patch("microsoft_teams.apps.routing.activity_context.OAuthCard"),
            patch("microsoft_teams.apps.routing.activity_context.CardAction"),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
        ):
            result = await ctx.sign_in()

        assert result is None
        ctx.api.bots.sign_in.get_resource.assert_called_once()
        assert mock_sender.send.called

    @pytest.mark.asyncio
    async def test_sign_in_creates_one_on_one_conversation_for_group_chat(self) -> None:
        """For group conversations, sign_in creates a 1:1 conversation before sending the OAuth card."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-001"
        mock_activity.conversation.is_group = True
        mock_activity.conversation.tenant_id = "tenant-001"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        ctx.api.users.token.get = AsyncMock(side_effect=Exception("no token"))

        one_on_one = MagicMock()
        one_on_one.id = "1on1-conv-id"
        ctx.api.conversations.create = AsyncMock(return_value=one_on_one)

        resource_response = MagicMock()
        resource_response.token_exchange_resource = MagicMock()
        resource_response.token_post_resource = MagicMock()
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api.bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.MessageActivityInput"),
            patch("microsoft_teams.apps.routing.activity_context.CreateConversationParams"),
            patch("microsoft_teams.apps.routing.activity_context.card_attachment"),
            patch("microsoft_teams.apps.routing.activity_context.OAuthCardAttachment"),
            patch("microsoft_teams.apps.routing.activity_context.OAuthCard"),
            patch("microsoft_teams.apps.routing.activity_context.CardAction"),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
        ):
            result = await ctx.sign_in()

        assert result is None
        ctx.api.conversations.create.assert_called_once()
        # one greeting message before the OAuth card, plus the OAuth card itself
        assert mock_sender.send.call_count >= 2

    @pytest.mark.asyncio
    async def test_sign_in_uses_signin_options_connection_name_override(self) -> None:
        """sign_in respects SignInOptions.connection_name override when fetching the existing token."""
        from microsoft_teams.apps.routing.activity_context import SignInOptions

        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-001"
        mock_activity.conversation.is_group = False

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.token.get = AsyncMock(side_effect=Exception("no token"))

        resource_response = MagicMock()
        resource_response.token_exchange_resource = MagicMock()
        resource_response.token_post_resource = MagicMock()
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api.bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        custom_options = SignInOptions(
            oauth_card_text="Custom prompt",
            sign_in_button_text="Login",
            connection_name="custom-connection",
        )

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "custom-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.MessageActivityInput"),
            patch("microsoft_teams.apps.routing.activity_context.card_attachment"),
            patch("microsoft_teams.apps.routing.activity_context.OAuthCardAttachment"),
            patch("microsoft_teams.apps.routing.activity_context.OAuthCard"),
            patch("microsoft_teams.apps.routing.activity_context.CardAction"),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
        ):
            result = await ctx.sign_in(options=custom_options)

        assert result is None
        token_get_params = ctx.api.users.token.get.call_args[0][0]
        assert token_get_params.connection_name == "custom-connection"


class TestActivityContextSignOut:
    """Tests for ActivityContext.sign_out()."""

    @pytest.mark.asyncio
    async def test_sign_out_logs_debug_on_success(self) -> None:
        """sign_out completes silently and logs a debug message when the API call succeeds."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-success"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.token.sign_out = AsyncMock(return_value=None)

        with patch.object(ctx.logger, "debug") as mock_log_debug:
            await ctx.sign_out()
            mock_log_debug.assert_called_once()
            logged = mock_log_debug.call_args[0][0]
            assert "user-success" in logged

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
