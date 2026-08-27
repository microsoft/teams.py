"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ConnectError, HTTPStatusError, Request, Response
from microsoft_teams.api import (
    Account,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    SentActivity,
    TargetedMessageInfoEntity,
    TokenExchangeResource,
    TokenStatus,
)
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.models.entity import QuotedReplyData, QuotedReplyEntity
from microsoft_teams.apps import TurnState, TurnStateContainer
from microsoft_teams.apps.oauth_state import get_pending_oauth_sign_ins
from microsoft_teams.apps.routing.activity_context import ActivityContext, SignInOptions
from microsoft_teams.apps.state import TurnStateLoader
from microsoft_teams.common import LocalStorage


def _create_activity_context(
    is_signed_in: bool = False,
    user_token: str | None = None,
    activity: Any = None,
    oauth_connection_names: list[str] | None = None,
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
        oauth_connection_names=oauth_connection_names,
    )
    return ctx, mock_activity_sender


def _http_status_error(status_code: int) -> HTTPStatusError:
    """Build an httpx.HTTPStatusError carrying the given status code."""
    request = Request("GET", "https://token.example/api/usertoken/GetToken")
    response = Response(status_code, request=request)
    return HTTPStatusError(f"HTTP {status_code}", request=request, response=response)


def pending_iso(epoch_seconds: float) -> str:
    """Render a pending sign-in timestamp the way it is stored on the wire."""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


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
    async def test_targeted_update_drops_recipient_from_payload(self) -> None:
        """
        Teams rejects targeted updates that carry a recipient, so the recipient only selects the
        targeted endpoint and is stripped from the outbound payload.
        """
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)

        # Create a targeted message update (has id set)
        activity = MessageActivityInput(text="Updated text").with_recipient(incoming_sender, is_targeted=True)
        activity.id = "existing-activity-id"  # This makes it an update

        result = await ctx.send(activity)

        ctx.api.conversations.activities.return_value.update_targeted.assert_called_once()
        ctx.api.conversations.activities.return_value.create_targeted.assert_not_called()
        activity_id, sent_activity = ctx.api.conversations.activities.return_value.update_targeted.call_args.args

        # The targeted endpoint is still chosen, but the wire payload carries no recipient
        assert activity_id == "existing-activity-id"
        assert sent_activity.text == "Updated text"
        assert sent_activity.recipient is None
        assert "recipient" not in sent_activity.model_dump(by_alias=True, exclude_none=True)

        # The caller still gets the recipient back
        assert result.activity_params.recipient is not None
        assert result.activity_params.recipient.id == incoming_sender.id
        assert result.activity_params.recipient.is_targeted is True
        mock_sender.send.assert_not_called()

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
    async def test_send_passes_inbound_agentic_user(self) -> None:
        """Sending from an Agent ID activity uses the inbound agentic user."""
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
    async def test_reply_passes_inbound_agentic_user(self) -> None:
        """Replying to an Agent ID activity uses the inbound agentic user."""
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
        loader = TurnStateLoader(LocalStorage())
        ctx.state = await loader.load("test-conversation", "user-001")
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

        resource_response = MagicMock()
        resource_response.token_exchange_resource = None
        resource_response.token_post_resource = None
        resource_response.sign_in_link = "https://login.example.com"
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})

        async def send_after_hint_persisted(activity):
            persisted = await loader.load("test-conversation", "user-001")
            assert persisted.user is not None
            assert "__oauth:pending:test-connection" in persisted.user
            return SentActivity(id="sent-activity-id", activity_params=activity)

        mock_sender.send.side_effect = send_after_hint_persisted
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
        # 1:1 (personal) sign-in cards are never targeted.
        sent_payload = mock_sender.send.call_args.args[0]
        assert sent_payload.recipient is not None
        assert sent_payload.recipient.is_targeted is not True
        assert ctx.state.user is not None
        # Two keys per connection with ISO 8601 values.
        # No SSO was offered here, so only the base marker is written.
        pending = ctx.state.user["__oauth:pending:test-connection"]
        assert "__oauth:pending:sso:test-connection" not in ctx.state.user
        assert datetime.fromisoformat(pending).tzinfo is not None

        reloaded = await loader.load("test-conversation", "user-001")
        assert reloaded.user is not None
        assert reloaded.user["__oauth:pending:test-connection"] == pending

    @pytest.mark.asyncio
    async def test_sign_in_restores_persisted_hints_when_card_send_fails(self) -> None:
        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )
        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        loader = TurnStateLoader(LocalStorage())
        ctx.state = await loader.load("test-conversation", "user-001")
        assert ctx.state.user is not None
        previous = pending_iso(time.time())
        ctx.state.user["__oauth:pending:existing-connection"] = previous
        await loader.save(ctx.state)

        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))
        resource_response = MagicMock(
            token_exchange_resource=None,
            token_post_resource=None,
            sign_in_link="https://login.example.com",
        )
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)
        mock_sender.send.side_effect = RuntimeError("send failed")

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
            pytest.raises(RuntimeError, match="send failed"),
        ):
            await ctx.sign_in()

        reloaded = await loader.load("test-conversation", "user-001")
        assert reloaded.user is not None
        assert reloaded.user["__oauth:pending:existing-connection"] == previous
        assert "__oauth:pending:test-connection" not in reloaded.user

    @pytest.mark.asyncio
    async def test_sign_in_restores_hint_when_pre_send_persistence_fails(self) -> None:
        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )
        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        ctx.state = await loader.load("test-conversation", "user-001")
        assert ctx.state.user is not None
        previous = pending_iso(time.time())
        ctx.state.user["__oauth:pending:existing-connection"] = previous
        await loader.save(ctx.state)
        storage.async_set = AsyncMock(side_effect=[RuntimeError("save failed"), None])

        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))
        resource_response = MagicMock(
            token_exchange_resource=None,
            token_post_resource=None,
            sign_in_link="https://login.example.com",
        )
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
            pytest.raises(RuntimeError, match="save failed"),
        ):
            await ctx.sign_in()

        mock_sender.send.assert_not_called()
        assert storage.async_set.await_count == 2
        assert ctx.state.user["__oauth:pending:existing-connection"] == previous
        assert "__oauth:pending:test-connection" not in ctx.state.user
        await loader.save(ctx.state)
        assert storage.async_set.await_count == 2

    @pytest.mark.asyncio
    async def test_sign_in_rollback_failure_does_not_mask_original_error(self) -> None:
        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )
        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        ctx.state = await loader.load("test-conversation", "user-001")
        ctx.logger = MagicMock()
        assert ctx.state.user is not None
        # A pre-existing hint means the rollback is a write (not a delete), so the
        # patched ``async_set`` below is what fails.
        ctx.state.user["__oauth:pending:existing-connection"] = pending_iso(time.time())
        await loader.save(ctx.state)

        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))
        resource_response = MagicMock(
            token_exchange_resource=None,
            token_post_resource=None,
            sign_in_link="https://login.example.com",
        )
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource_response)
        mock_sender.send.side_effect = RuntimeError("send failed")
        # First write (the pre-send flush) succeeds; the rollback write blows up.
        storage.async_set = AsyncMock(side_effect=[None, RuntimeError("rollback save failed")])

        token_state = MagicMock()
        token_state.model_dump = MagicMock(return_value={"connection_name": "test-connection"})
        with (
            patch(
                "microsoft_teams.apps.routing.activity_context.TokenExchangeState",
                return_value=token_state,
            ),
            patch("microsoft_teams.apps.routing.activity_context.GetBotSignInResourceParams"),
            pytest.raises(RuntimeError, match="send failed"),
        ):
            await ctx.sign_in()

        ctx.logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_sign_in_group_chat_sends_targeted_card(self) -> None:
        """In a group chat, sign_in sends the OAuth card as a targeted message directly in
        the conversation (no 1:1 fallback) and keeps the token exchange resource for SSO."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_ = Account(id="user-001")
        mock_activity.conversation.is_group = True
        mock_activity.conversation.conversation_type = "groupChat"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        ctx.state = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="test-conversation",
            user=TurnState(),
            user_id="user-001",
        )
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))
        ctx.api.conversations.create = AsyncMock()

        resource_response = MagicMock()
        resource_response.token_exchange_resource = TokenExchangeResource(
            id="exchange-id",
            uri="api://resource",
            provider_id="provider",
        )
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
        # No 1:1 fallback conversation is created.
        ctx.api.conversations.create.assert_not_called()
        # A single OAuth card is sent, targeted to the requesting user.
        ctx.api.conversations.create_targeted_activity.assert_called_once()
        sent_payload = ctx.api.conversations.create_targeted_activity.call_args.args[1]
        assert sent_payload.recipient is not None
        assert sent_payload.recipient.is_targeted is True
        # SSO token exchange remains available in group chats.
        assert sent_payload.attachments[0].content.token_exchange_resource is resource_response.token_exchange_resource
        assert ctx.state.user is not None
        # SSO was offered, so both markers are written.
        assert "__oauth:pending:test-connection" in ctx.state.user
        assert "__oauth:pending:sso:test-connection" in ctx.state.user

    @pytest.mark.asyncio
    async def test_sign_in_channel_targets_and_omits_token_exchange(self) -> None:
        """In a channel, sign_in sends a targeted OAuth card and omits the token exchange
        resource (channels can't do silent SSO) so Teams renders the sign-in button."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_ = Account(id="user-001")
        mock_activity.conversation.is_group = True
        mock_activity.conversation.conversation_type = "channel"

        ctx, mock_sender = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))
        ctx.api.conversations.create = AsyncMock()

        resource_response = MagicMock()
        resource_response.token_exchange_resource = MagicMock()
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
        ctx.api.conversations.create.assert_not_called()
        ctx.api.conversations.create_targeted_activity.assert_called_once()
        sent_payload = ctx.api.conversations.create_targeted_activity.call_args.args[1]
        assert sent_payload.recipient is not None
        assert sent_payload.recipient.is_targeted is True
        # SSO isn't possible in channels, so the token exchange resource is omitted.
        assert sent_payload.attachments[0].content.token_exchange_resource is None

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
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

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

    @pytest.mark.asyncio
    async def test_sign_in_stores_pending_hints_newest_first(self) -> None:
        """Pending hints are read back with the most recent sign-in first."""
        from microsoft_teams.apps.routing.activity_context import SignInOptions

        mock_activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )

        ctx, _ = _create_activity_context(activity=mock_activity)
        loader = TurnStateLoader(LocalStorage())
        ctx.state = await loader.load("test-conversation", "user-001")
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

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
            await ctx.sign_in()
            await ctx.sign_in(options=SignInOptions(connection_name="second-connection"))

        assert ctx.state.user is not None
        # Storage is one key per connection and carries no ordering of its own; the
        # newest-first guarantee is applied when the hints are read back.
        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(ctx.state)] == [
            "second-connection",
            "test-connection",
        ]

        reloaded = await loader.load("test-conversation", "user-001")
        assert reloaded.user is not None
        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(reloaded)] == [
            "second-connection",
            "test-connection",
        ]


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
    async def test_sign_out_propagates_token_service_failure(self) -> None:
        """sign_out surfaces Token Service failures instead of swallowing them.

        A failed sign-out leaves the token in place. Logging and returning would
        tell the caller the user is signed out when they are not.
        """
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-003"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.sign_out = AsyncMock(side_effect=_http_status_error(500))

        with pytest.raises(HTTPStatusError):
            await ctx.sign_out()


class TestActivityContextTokenHelpers:
    """Tests for sign_out(connection_name=), get_user_token, and get_token_status."""

    @pytest.mark.asyncio
    async def test_sign_out_uses_override_connection_name(self) -> None:
        """sign_out(connection_name=...) targets the named connection."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.sign_out = AsyncMock(return_value=None)

        await ctx.sign_out(connection_name="github")

        ctx.api.users.sign_out.assert_awaited_once()
        params = ctx.api.users.sign_out.call_args[0][0]
        assert params.connection_name == "github"
        assert params.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_sign_out_defaults_to_ctx_connection(self) -> None:
        """sign_out() with no argument falls back to the context's connection."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.sign_out = AsyncMock(return_value=None)

        await ctx.sign_out()

        params = ctx.api.users.sign_out.call_args[0][0]
        assert params.connection_name == "test-connection"

    @pytest.mark.asyncio
    async def test_get_user_token_returns_token(self) -> None:
        """get_user_token returns the token for the requested connection."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        token_res = MagicMock()
        token_res.token = "the-token"
        ctx.api.users.get_token = AsyncMock(return_value=token_res)

        result = await ctx.get_user_token(connection_name="github")

        assert result == "the-token"
        params = ctx.api.users.get_token.call_args[0][0]
        assert params.connection_name == "github"
        assert params.user_id == "user-1"

    @pytest.mark.asyncio
    async def test_get_user_token_defaults_to_ctx_connection(self) -> None:
        """get_user_token() defaults to the context's connection name."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        token_res = MagicMock()
        token_res.token = "the-token"
        ctx.api.users.get_token = AsyncMock(return_value=token_res)

        await ctx.get_user_token()

        params = ctx.api.users.get_token.call_args[0][0]
        assert params.connection_name == "test-connection"

    @pytest.mark.asyncio
    async def test_get_user_token_returns_none_when_not_signed_in(self) -> None:
        """A 404 from the Token Service means 'not signed in' and yields None."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

        result = await ctx.get_user_token()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_token_propagates_service_errors(self) -> None:
        """A non-404 HTTP error (e.g. Token Service down) is surfaced, not masked as logged-out."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(500))

        with pytest.raises(HTTPStatusError):
            await ctx.get_user_token()

    @pytest.mark.asyncio
    async def test_get_user_token_propagates_non_http_errors(self) -> None:
        """Network/transport errors propagate rather than being reported as not signed in."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token = AsyncMock(side_effect=RuntimeError("connection reset"))

        with pytest.raises(RuntimeError):
            await ctx.get_user_token()

    @pytest.mark.asyncio
    async def test_get_token_status_returns_all_connections(self) -> None:
        """get_token_status makes a single call and returns the status list unfiltered."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        statuses = [MagicMock(), MagicMock()]
        ctx.api.users.get_token_status = AsyncMock(return_value=statuses)

        result = await ctx.get_token_status()

        assert result is statuses
        ctx.api.users.get_token_status.assert_awaited_once()
        params = ctx.api.users.get_token_status.call_args[0][0]
        assert params.include_filter is None
        assert params.user_id == "user-1"
        assert params.channel_id == "msteams"

    @pytest.mark.asyncio
    async def test_get_token_status_propagates_errors(self) -> None:
        """Unlike get_user_token, get_token_status lets service failures surface."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token_status = AsyncMock(side_effect=RuntimeError("service down"))

        with pytest.raises(RuntimeError):
            await ctx.get_token_status()


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


class TestSignInCachedTokenErrorPrecedence:
    """sign_in only falls back to a card when the Token Service says 404."""

    @staticmethod
    def _context() -> tuple[ActivityContext[Any], MagicMock]:
        activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(id="test-conversation", is_group=False),
        )
        ctx, sender = _create_activity_context(activity=activity)
        resource = MagicMock()
        resource.token_exchange_resource = None
        resource.token_post_resource = None
        resource.sign_in_link = "https://login.example.com"
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource)
        return ctx, sender

    @pytest.mark.asyncio
    async def test_404_falls_back_to_the_oauth_card(self) -> None:
        """404 is the only "user has no token yet" answer."""
        ctx, sender = self._context()
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

        assert await ctx.sign_in() is None
        sender.send.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 401, 412, 429, 500, 503])
    async def test_other_http_statuses_propagate(self, status_code: int) -> None:
        """A rejected request or an outage is not a signed-out user.

        Swallowing these showed the user a sign-in card during an incident and
        hid the real cause from the developer.
        """
        ctx, sender = self._context()
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(status_code))

        with pytest.raises(HTTPStatusError):
            await ctx.sign_in()
        sender.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_transport_failure_propagates(self) -> None:
        """A connection error never reached the Token Service at all."""
        ctx, sender = self._context()
        ctx.api.users.get_token = AsyncMock(side_effect=ConnectError("connection refused"))

        with pytest.raises(ConnectError):
            await ctx.sign_in()
        sender.send.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_programming_error_propagates(self) -> None:
        """A bug in the token path must not be reported as "please sign in"."""
        ctx, sender = self._context()
        ctx.api.users.get_token = AsyncMock(side_effect=TypeError("bad argument"))

        with pytest.raises(TypeError):
            await ctx.sign_in()
        sender.send.assert_not_awaited()


class TestSignInOverrideActivity:
    """SignInOptions.override_sign_in_activity replaces the default OAuth card."""

    @staticmethod
    def _context(is_group: bool = False, conversation_type: str | None = None):
        activity = MessageActivity(
            id="activity-id",
            channel_id="msteams",
            from_=Account(id="user-001"),
            recipient=Account(id="bot-id"),
            conversation=ConversationAccount(
                id="test-conversation",
                is_group=is_group,
                conversation_type=conversation_type,
            ),
        )
        ctx, sender = _create_activity_context(activity=activity)
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))
        resource = MagicMock()
        resource.token_exchange_resource = TokenExchangeResource(id="exchange-id")
        resource.token_post_resource = None
        resource.sign_in_link = "https://login.example.com"
        ctx.api._bots.sign_in.get_resource = AsyncMock(return_value=resource)
        return ctx, sender

    @pytest.mark.asyncio
    async def test_override_activity_is_sent_instead_of_the_card(self) -> None:
        """Red-green: before this change the option was read by nothing at all."""
        ctx, sender = self._context()
        override = MessageActivityInput(text="custom sign-in prompt")

        assert await ctx.sign_in(SignInOptions(override_sign_in_activity=lambda *_: override)) is None

        sent = sender.send.call_args[0][0]
        assert sent is override
        assert sent.attachments is None

    @pytest.mark.asyncio
    async def test_override_receives_the_sign_in_resource(self) -> None:
        """The callback needs the resource to build its own sign-in affordance."""
        ctx, _ = self._context()
        seen: list[Any] = []

        def build(exchange_resource, post_resource, link):
            seen.append((exchange_resource, post_resource, link))
            return MessageActivityInput(text="custom")

        await ctx.sign_in(SignInOptions(override_sign_in_activity=build))

        assert len(seen) == 1
        exchange_resource, _, link = seen[0]
        assert exchange_resource is not None and exchange_resource.id == "exchange-id"
        assert link == "https://login.example.com"

    @pytest.mark.asyncio
    async def test_override_in_a_channel_gets_no_exchange_resource(self) -> None:
        """Channels cannot exchange silently, so the override must not offer it."""
        ctx, _ = self._context(is_group=True, conversation_type="channel")
        seen: list[Any] = []

        def build(exchange_resource, post_resource, link):
            seen.append(exchange_resource)
            return MessageActivityInput(text="custom")

        await ctx.sign_in(SignInOptions(override_sign_in_activity=build))

        assert seen == [None]

    @pytest.mark.asyncio
    async def test_override_is_targeted_in_group_conversations(self) -> None:
        """An override replaces the card, not the group-chat privacy rule."""
        ctx, _ = self._context(is_group=True)

        await ctx.sign_in(SignInOptions(override_sign_in_activity=lambda *_: MessageActivityInput(text="custom")))

        ctx.api.conversations.create_targeted_activity.assert_called_once()
        sent = ctx.api.conversations.create_targeted_activity.call_args.args[1]
        assert sent.recipient is not None
        assert sent.recipient.id == "user-001"
        assert sent.recipient.is_targeted is True

    @pytest.mark.asyncio
    async def test_override_keeps_its_own_recipient(self) -> None:
        """An explicit recipient is the caller's decision and is left alone.

        It is also not silently promoted to a targeted message: targeting follows
        ``recipient.is_targeted``, which the override did not set.
        """
        ctx, sender = self._context(is_group=True)
        chosen = Account(id="someone-else")

        await ctx.sign_in(
            SignInOptions(override_sign_in_activity=lambda *_: MessageActivityInput(text="custom", recipient=chosen))
        )

        ctx.api.conversations.create_targeted_activity.assert_not_called()
        assert sender.send.call_args[0][0].recipient.id == "someone-else"

    @pytest.mark.asyncio
    async def test_override_still_records_pending_attribution(self) -> None:
        """Routing the callback must not depend on which activity was sent."""
        loader = TurnStateLoader(LocalStorage())
        ctx, _ = self._context()
        ctx.state = await loader.load("test-conversation", "user-001")

        await ctx.sign_in(
            SignInOptions(
                connection_name="graph",
                override_sign_in_activity=lambda *_: MessageActivityInput(text="custom"),
            )
        )

        pending = get_pending_oauth_sign_ins(ctx.state)
        assert [hint.connection_name for hint in pending] == ["graph"]
        assert pending[0].sso_offered is True

    @pytest.mark.asyncio
    async def test_override_send_failure_rolls_back_pending(self) -> None:
        """A card that never went out must not leave a hint that mis-routes."""
        loader = TurnStateLoader(LocalStorage())
        ctx, sender = self._context()
        ctx.state = await loader.load("test-conversation", "user-001")
        sender.send.side_effect = RuntimeError("send failed")

        with pytest.raises(RuntimeError, match="send failed"):
            await ctx.sign_in(
                SignInOptions(
                    connection_name="graph",
                    override_sign_in_activity=lambda *_: MessageActivityInput(text="custom"),
                )
            )

        assert get_pending_oauth_sign_ins(ctx.state) == []


class TestGetTokenStatusRegistryAware:
    """get_token_status corrects the bulk call for registered flows."""

    @staticmethod
    def _context(connection_names: list[str] | None = None):
        activity = MagicMock()
        activity.channel_id = "msteams"
        activity.from_.id = "user-1"
        return _create_activity_context(activity=activity, oauth_connection_names=connection_names)[0]

    @staticmethod
    def _status(connection_name: str, has_token: bool) -> TokenStatus:
        return TokenStatus(
            channel_id="msteams",
            connection_name=connection_name,
            has_token=has_token,
            service_provider_display_name="Contoso",
        )

    @pytest.mark.asyncio
    async def test_without_registered_flows_the_bulk_result_is_returned_verbatim(self) -> None:
        """Legacy single-connection apps see exactly what the service said."""
        ctx = self._context()
        statuses = [self._status("legacy", False)]
        ctx.api.users.get_token_status = AsyncMock(return_value=statuses)
        ctx.api.users.get_token = AsyncMock(side_effect=AssertionError("must not probe"))

        assert await ctx.get_token_status() is statuses

    @pytest.mark.asyncio
    async def test_false_status_for_a_registered_flow_is_corrected(self) -> None:
        """The bulk call can lag a token that was just written.

        Red-green: without the per-flow lookup this reports has_token=False for a
        connection the user is demonstrably signed in to.
        """
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("graph", False)])
        ctx.api.users.get_token = AsyncMock(return_value=MagicMock(token="a-token"))

        result = await ctx.get_token_status()

        assert [(s.connection_name, s.has_token) for s in result] == [("graph", True)]

    @pytest.mark.asyncio
    async def test_a_genuine_miss_stays_false(self) -> None:
        """A confirmed absence is not rewritten."""
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("graph", False)])
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

        result = await ctx.get_token_status()

        assert [(s.connection_name, s.has_token) for s in result] == [("graph", False)]

    @pytest.mark.asyncio
    async def test_a_registered_flow_missing_from_the_bulk_result_is_added(self) -> None:
        """The service only lists connections it knows; a flow may be absent."""
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("legacy", True)])
        ctx.api.users.get_token = AsyncMock(return_value=MagicMock(token="a-token"))

        result = await ctx.get_token_status()

        assert [(s.connection_name, s.has_token) for s in result] == [("legacy", True), ("graph", True)]

    @pytest.mark.asyncio
    async def test_unregistered_connections_are_passed_through_untouched(self) -> None:
        """Only registered flows are re-checked; everything else is verbatim."""
        ctx = self._context(["graph"])
        legacy = self._status("legacy", False)
        ctx.api.users.get_token_status = AsyncMock(return_value=[legacy, self._status("graph", True)])
        probes: list[str] = []

        async def probe(params):
            probes.append(params.connection_name)
            return MagicMock(token="a-token")

        ctx.api.users.get_token = AsyncMock(side_effect=probe)

        result = await ctx.get_token_status()

        assert result[0] is legacy
        assert probes == []

    @pytest.mark.asyncio
    async def test_registry_casing_is_matched_case_insensitively(self) -> None:
        """The service may echo a different casing than the app registered."""
        ctx = self._context(["Graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("GRAPH", False)])
        ctx.api.users.get_token = AsyncMock(return_value=MagicMock(token="a-token"))

        result = await ctx.get_token_status()

        # Corrected in place: one row, keeping the service's own casing.
        assert [(s.connection_name, s.has_token) for s in result] == [("GRAPH", True)]

    @pytest.mark.asyncio
    async def test_order_and_shape_are_preserved(self) -> None:
        """Existing rows keep their order; additions go on the end."""
        ctx = self._context(["b", "missing"])
        ctx.api.users.get_token_status = AsyncMock(
            return_value=[self._status("a", True), self._status("b", True), self._status("c", False)]
        )
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

        result = await ctx.get_token_status()

        assert [s.connection_name for s in result] == ["a", "b", "c", "missing"]

    @pytest.mark.asyncio
    async def test_non_404_lookup_failure_propagates(self) -> None:
        """An outage during the correction is not silently reported as False."""
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("graph", False)])
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(503))

        with pytest.raises(HTTPStatusError):
            await ctx.get_token_status()
