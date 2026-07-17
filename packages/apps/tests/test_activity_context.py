"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import (
    Account,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    SentActivity,
    TargetedMessageInfoEntity,
)
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.models.entity import QuotedReplyData, QuotedReplyEntity
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
    activities = MagicMock()
    activities.create = mock_activity_sender.send
    activities.update = AsyncMock(
        return_value=SentActivity(
            id="updated-activity-id",
            activity_params=MessageActivityInput(text="updated"),
        )
    )
    activities.create_targeted = AsyncMock(
        return_value=SentActivity(
            id="targeted-activity-id",
            activity_params=MessageActivityInput(text="targeted"),
        )
    )
    activities.update_targeted = AsyncMock(
        return_value=SentActivity(
            id="updated-targeted-activity-id",
            activity_params=MessageActivityInput(text="updated targeted"),
        )
    )
    api = MagicMock()
    api.conversations.activities.return_value = activities
    api.clone.return_value = api

    async def create_activity(conversation_id: str, activity: Any) -> SentActivity:
        api.conversations.activities(conversation_id)
        return await activities.create(activity)

    async def update_activity(conversation_id: str, activity_id: str, activity: Any) -> SentActivity:
        api.conversations.activities(conversation_id)
        return await activities.update(activity_id, activity)

    async def create_targeted_activity(conversation_id: str, activity: Any) -> SentActivity:
        api.conversations.activities(conversation_id)
        return await activities.create_targeted(activity)

    async def update_targeted_activity(conversation_id: str, activity_id: str, activity: Any) -> SentActivity:
        api.conversations.activities(conversation_id)
        return await activities.update_targeted(activity_id, activity)

    api.conversations.create_activity = AsyncMock(side_effect=create_activity)
    api.conversations.update_activity = AsyncMock(side_effect=update_activity)
    api.conversations.create_targeted_activity = AsyncMock(side_effect=create_targeted_activity)
    api.conversations.update_targeted_activity = AsyncMock(side_effect=update_targeted_activity)

    conversation_ref = ConversationReference(
        bot=Account(id="bot-id", name="Test Bot"),
        conversation=ConversationAccount(id="test-conversation"),
        channel_id="msteams",
        service_url="https://service.example",
    )

    ctx = ActivityContext(
        activity=mock_activity,
        app_id="test-app-id",
        storage=MagicMock(),
        api=api,
        user_token=user_token,
        conversation_ref=conversation_ref,
        is_signed_in=is_signed_in,
        connection_name="test-connection",
        app_token=MagicMock(),
        cloud=PUBLIC,
    )
    return ctx, mock_activity_sender


class TestActivityContextSendTargeted:
    """Tests for ActivityContext.send() with targeted message recipient inference."""

    def _create_activity_context(
        self, from_account: Account, *, is_incoming_targeted: bool = False
    ) -> tuple[ActivityContext[Any], MagicMock]:
        """Create an ActivityContext for testing with a mock activity sender."""
        recipient = Account(id="bot-id", name="Test Bot", is_targeted=True if is_incoming_targeted else None)
        activity = MessageActivity(
            id="incoming-activity-id",
            text="Incoming message",
            from_=from_account,
            recipient=recipient,
            conversation=ConversationAccount(id="test-conversation"),
        )
        return _create_activity_context(activity=activity)

    @pytest.mark.asyncio
    async def test_defaults_send_to_targeted_when_inbound_message_is_targeted(self) -> None:
        """A plain send from a targeted inbound message defaults to targeted."""
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender, is_incoming_targeted=True)

        await ctx.send("Secret message")

        mock_sender.send.assert_not_called()
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.text == "Secret message"
        assert sent_activity.from_ == ctx.conversation_ref.bot
        assert sent_activity.conversation == ctx.conversation_ref.conversation
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == incoming_sender.id
        assert sent_activity.recipient.name == incoming_sender.name
        assert sent_activity.recipient.is_targeted is True
        assert sent_activity.entities is not None
        assert any(isinstance(entity, TargetedMessageInfoEntity) for entity in sent_activity.entities)
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        ctx.api.conversations.activities.return_value.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_reply_defaults_to_targeted_when_inbound_message_is_targeted(self) -> None:
        """reply() also defaults to targeted for targeted inbound messages."""
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender, is_incoming_targeted=True)

        await ctx.reply("Private reply")

        mock_sender.send.assert_not_called()
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert isinstance(sent_activity, MessageActivityInput)
        assert sent_activity.reply_to_id is None
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == incoming_sender.id
        assert sent_activity.recipient.is_targeted is True
        assert sent_activity.entities is not None
        assert any(
            isinstance(entity, TargetedMessageInfoEntity) and entity.message_id == "incoming-activity-id"
            for entity in sent_activity.entities
        )

    @pytest.mark.asyncio
    async def test_explicit_public_send_opts_out_from_targeted_inbound_message(self) -> None:
        """Supplying a non-targeted recipient keeps the send public."""
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender, is_incoming_targeted=True)

        await ctx.send(MessageActivityInput(text="Public message").with_recipient(incoming_sender))

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == incoming_sender.id
        assert sent_activity.recipient.is_targeted is None
        assert sent_activity.entities is None

    @pytest.mark.asyncio
    async def test_different_conversation_does_not_default_to_targeted(self) -> None:
        """Sending to a different conversation should not inherit targeted routing."""
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender, is_incoming_targeted=True)
        other_ref = ConversationReference(
            bot=Account(id="bot-id", name="Test Bot"),
            conversation=ConversationAccount(id="other-conversation"),
            channel_id="msteams",
            service_url="https://service.example",
        )

        await ctx.send("Cross-post", other_ref)

        mock_sender.send.assert_called_once()
        sent_activity = mock_sender.send.call_args[0][0]
        ctx.api.conversations.activities.assert_called_once_with("other-conversation")
        assert sent_activity.recipient is None
        assert sent_activity.entities is None

    @pytest.mark.asyncio
    async def test_explicit_targeted_send_from_public_inbound_does_not_add_targeted_message_info(self) -> None:
        """Generic targeted sends should not reference a public inbound message."""
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)
        activity = MessageActivityInput(text="Targeted send").with_recipient(incoming_sender, is_targeted=True)

        await ctx.send(activity)

        mock_sender.send.assert_not_called()
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.is_targeted is True
        assert sent_activity.entities is None

    @pytest.mark.asyncio
    async def test_targeted_outbound_strips_quoted_reply_metadata(self) -> None:
        """Targeted responses remove quotedReply entities and quoted placeholders."""
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender, is_incoming_targeted=True)
        activity = MessageActivityInput(
            text='<quoted messageId="incoming-activity-id"/> Secret',
            entities=[QuotedReplyEntity(quoted_reply=QuotedReplyData(message_id="incoming-activity-id"))],
        )

        await ctx.send(activity)

        mock_sender.send.assert_not_called()
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert sent_activity.text == "Secret"
        assert sent_activity.entities is not None
        assert all(not isinstance(entity, QuotedReplyEntity) for entity in sent_activity.entities)
        assert any(isinstance(entity, TargetedMessageInfoEntity) for entity in sent_activity.entities)

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
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        mock_sender.send.assert_not_called()

        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]

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

        ctx.api.conversations.activities.return_value.update_targeted.assert_called_once()
        sent_activity = ctx.api.conversations.activities.return_value.update_targeted.call_args.args[1]

        # Verify recipient was preserved
        assert sent_activity.recipient is not None
        assert sent_activity.recipient.id == incoming_sender.id
        assert sent_activity.recipient.name == incoming_sender.name
        assert sent_activity.recipient.is_targeted is True

    @pytest.mark.asyncio
    async def test_send_existing_activity_updates(self) -> None:
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)
        activity = MessageActivityInput(text="Updated message")
        activity.id = "existing-msg-id"

        await ctx.send(activity)

        ctx.api.conversations.activities.return_value.update.assert_called_once_with(
            "existing-msg-id",
            activity,
        )
        mock_sender.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_targeted_send_in_personal_chat_raises(self) -> None:
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, _ = self._create_activity_context(from_account=incoming_sender)
        ctx.conversation_ref.conversation.conversation_type = "personal"
        activity = MessageActivityInput(text="Nope").with_recipient(incoming_sender, is_targeted=True)

        with pytest.raises(ValueError, match="Targeted messages are not supported in 1:1"):
            await ctx.send(activity)

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
        mock_sender.send.assert_not_called()
        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]

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

    @pytest.mark.asyncio
    async def test_send_passes_inbound_agentic_identity(self) -> None:
        """Sending from an Agent ID activity uses the inbound agentic identity."""
        recipient = Account(
            id="bot-id",
            name="Test Bot",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        activity = MessageActivity(
            id="incoming-activity-id",
            text="Incoming message",
            from_=Account(id="user-id", name="Test User"),
            recipient=recipient,
            conversation=ConversationAccount(id="test-conversation"),
        )
        ctx, mock_sender = _create_activity_context(activity=activity)

        await ctx.send("Hello")

        mock_sender.send.assert_called_once()
        ctx.api.clone.assert_called_once_with(
            service_url=ctx.conversation_ref.service_url,
            agentic_identity=recipient.agentic_identity,
        )


class TestActivityContextReply:
    """Tests for ActivityContext.reply()."""

    @pytest.mark.asyncio
    async def test_reply_with_string(self) -> None:
        """reply() with a plain string stamps a quotedReply entity and placeholder."""
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

    @pytest.mark.asyncio
    async def test_reply_passes_inbound_agentic_identity(self) -> None:
        """Replying to an Agent ID activity uses the inbound agentic identity."""
        recipient = Account(
            id="bot-id",
            name="Test Bot",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        activity = MessageActivity(
            id="incoming-activity-id",
            text="Incoming message",
            from_=Account(id="user-id", name="Test User"),
            recipient=recipient,
            conversation=ConversationAccount(id="test-conversation"),
        )
        ctx, mock_sender = _create_activity_context(activity=activity)

        await ctx.reply("Hello")

        mock_sender.send.assert_called_once()
        ctx.api.clone.assert_called_once_with(
            service_url=ctx.conversation_ref.service_url,
            agentic_identity=recipient.agentic_identity,
        )


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
        mock_activity.from_ = Account(id="user-001")
        mock_activity.conversation.is_group = False

        ctx, _ = _create_activity_context(activity=mock_activity)

        token_response = MagicMock()
        token_response.token = "existing-token-value"
        ctx.api.users.get_token = AsyncMock(return_value=token_response)

        result = await ctx.sign_in()

        assert result == "existing-token-value"
        ctx.api.users.get_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_sends_oauth_card_when_no_existing_token(self) -> None:
        """sign_in falls through to OAuth card flow when token API fails, returns None."""
        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )

        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=Exception("no token"))

        resource_response = MagicMock()
        resource_response.token_exchange_resource = None
        resource_response.token_post_resource = None
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
        ):
            result = await ctx.sign_in()

        assert result is None
        ctx.api._bots.sign_in.get_resource.assert_called_once()
        assert mock_sender.send.called

    @pytest.mark.asyncio
    async def test_sign_in_creates_one_on_one_conversation_for_group_chat(self) -> None:
        """For group conversations, sign_in creates a 1:1 conversation before sending the OAuth card."""
        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=True, tenant_id="tenant-001"),
        )

        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=Exception("no token"))

        one_on_one = MagicMock()
        one_on_one.id = "1on1-conv-id"
        ctx.api.conversations.create = AsyncMock(return_value=one_on_one)

        resource_response = MagicMock()
        resource_response.token_exchange_resource = None
        resource_response.token_post_resource = None
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.CreateConversationParams"),
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

        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=Exception("no token"))

        resource_response = MagicMock()
        resource_response.token_exchange_resource = None
        resource_response.token_post_resource = None
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

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
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
        ):
            result = await ctx.sign_in(options=custom_options)

        assert result is None
        token_get_params = ctx.api.users.get_token.call_args[0][0]
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
        ctx.api.users.sign_out = AsyncMock(return_value=None)

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
        ctx.api.users.sign_out = AsyncMock(side_effect=Exception("API failure"))

        with patch.object(ctx.logger, "error") as mock_log_error:
            # Should not raise
            await ctx.sign_out()

            mock_log_error.assert_called_once()
            logged_message = mock_log_error.call_args[0][0]
            assert "Failed to sign out user" in logged_message


class TestActivityContextPromptPreview:
    """Tests for reactive auto-population of targetedMessageInfo entity."""

    def _make_targeted_activity(self, activity_id: str = "1772129782775") -> MessageActivity:
        return MessageActivity(
            id=activity_id,
            text="Hello from slash command",
            from_=Account(id="user-123", name="Test User"),
            recipient=Account(id="bot-456", name="Bot", is_targeted=True),
            conversation=ConversationAccount(id="test-conversation"),
        )

    def _make_non_targeted_activity(self) -> MessageActivity:
        return MessageActivity(
            id="normal-msg-id",
            text="Normal message",
            from_=Account(id="user-123", name="Test User"),
            recipient=Account(id="bot-456", name="Bot"),
            conversation=ConversationAccount(id="test-conversation"),
        )

    @pytest.mark.asyncio
    async def test_send_auto_adds_targeted_message_info_entity(self) -> None:
        """When replying to a targeted message, the SDK auto-adds targetedMessageInfo."""
        activity = self._make_targeted_activity("1772129782775")
        ctx, mock_sender = _create_activity_context(activity=activity)

        await ctx.send("Here is your agenda")

        mock_sender.send.assert_not_called()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 1
        entity = sent_activity.entities[0]
        assert isinstance(entity, TargetedMessageInfoEntity)
        assert entity.message_id == "1772129782775"
        assert entity.type == "targetedMessageInfo"

    @pytest.mark.asyncio
    async def test_send_does_not_add_entity_for_non_targeted(self) -> None:
        """When replying to a normal message, no targetedMessageInfo is added."""
        activity = self._make_non_targeted_activity()
        ctx, mock_sender = _create_activity_context(activity=activity)

        await ctx.send("Normal reply")

        sent_activity = mock_sender.send.call_args[0][0]
        assert sent_activity.entities is None

    @pytest.mark.asyncio
    async def test_send_does_not_duplicate_entity_if_already_present(self) -> None:
        """If the developer already added targetedMessageInfo, the SDK does not duplicate it."""
        activity = self._make_targeted_activity("1772129782775")
        ctx, mock_sender = _create_activity_context(activity=activity)

        msg = MessageActivityInput(text="Reply").add_entity(TargetedMessageInfoEntity(message_id="custom-id"))
        await ctx.send(msg)

        mock_sender.send.assert_not_called()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert sent_activity.entities is not None
        assert len(sent_activity.entities) == 1
        assert sent_activity.entities[0].message_id == "custom-id"

    @pytest.mark.asyncio
    async def test_reply_auto_adds_targeted_message_info_entity(self) -> None:
        """reply() also auto-adds targetedMessageInfo for targeted messages.
        The blockquote is added by reply(), then stripped by add_targeted_message_info
        in send() to avoid collision with prompt preview."""
        activity = self._make_targeted_activity("1772129782775")
        ctx, mock_sender = _create_activity_context(activity=activity)

        await ctx.reply("Reply with prompt preview")

        mock_sender.send.assert_not_called()
        sent_activity = ctx.api.conversations.activities.return_value.create_targeted.call_args.args[0]
        assert sent_activity.entities is not None
        targeted_entities = [e for e in sent_activity.entities if isinstance(e, TargetedMessageInfoEntity)]
        assert len(targeted_entities) == 1
        assert targeted_entities[0].message_id == "1772129782775"

        # quotedReply entities should be stripped by add_targeted_message_info
        assert not any(getattr(e, "type", None) == "quotedReply" for e in sent_activity.entities)

    @pytest.mark.asyncio
    async def test_send_does_not_add_entity_for_non_message_activity(self) -> None:
        """Non-message activities (e.g. typing) should not get targetedMessageInfo attached."""
        activity = self._make_targeted_activity("1772129782775")
        ctx, mock_sender = _create_activity_context(activity=activity)

        await ctx.send(TypingActivityInput())

        sent_activity = mock_sender.send.call_args[0][0]
        assert sent_activity.entities is None
