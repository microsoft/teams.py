"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# pyright: basic

import time
import warnings
from contextlib import contextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, Generator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ConnectError, HTTPStatusError, Request, Response
from microsoft_teams.api import (
    Account,
    Activity,
    AdaptiveCardInvokeActivity,
    ChannelData,
    ConversationAccount,
    ConversationReference,
    MessageActivity,
    MessageActivityInput,
    MessageExtensionFetchTaskInvokeActivity,
    MessageExtensionQueryInvokeActivity,
    MessageExtensionSubmitActionInvokeActivity,
    MessageSubmitActionInvokeActivity,
    SentActivity,
    SourceInfo,
    TargetedMessageInfoEntity,
    TaskFetchInvokeActivity,
    TaskSubmitInvokeActivity,
    TokenExchangeResource,
    TokenProtocol,
    TokenStatus,
)
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.clients.conversation import ConversationClient
from microsoft_teams.api.models.entity import QuotedReplyData, QuotedReplyEntity
from microsoft_teams.apps import ActivityEvent, App, StreamOptions, StreamReplyChain, TurnState, TurnStateContainer
from microsoft_teams.apps.events import CoreActivity
from microsoft_teams.apps.oauth_state import get_pending_oauth_sign_ins
from microsoft_teams.apps.routing.activity_context import ActivityContext, SignInOptions
from microsoft_teams.apps.state import TurnStateLoader
from microsoft_teams.common import ExperimentalWarning, LocalStorage
from microsoft_teams.common.http import Client, ClientOptions
from pydantic import TypeAdapter, ValidationError


def _capture_oauth_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[list[tuple[str, str]], MagicMock]:
    calls: list[tuple[str, str]] = []
    telemetry = MagicMock(result="operation_failed")

    @contextmanager
    def trace(connection_name: str, operation: str) -> Generator[tuple[MagicMock, MagicMock], None, None]:
        calls.append((connection_name, operation))
        yield MagicMock(), telemetry

    monkeypatch.setattr(
        "microsoft_teams.apps.routing.activity_context.trace_oauth_operation",
        trace,
    )
    return calls, telemetry


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

        with pytest.warns(DeprecationWarning):
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
    async def test_targeted_send_in_personal_chat_uses_targeted_endpoint(self) -> None:
        incoming_sender = Account(id="user-123", name="Test User")
        ctx, mock_sender = self._create_activity_context(from_account=incoming_sender)
        ctx.conversation_ref.conversation.conversation_type = "personal"
        activity = MessageActivityInput(text="Private reply").with_recipient(incoming_sender, is_targeted=True)

        await ctx.send(activity)

        ctx.api.conversations.activities.return_value.create_targeted.assert_called_once_with(activity)
        ctx.api.conversations.activities.return_value.create.assert_not_called()
        mock_sender.send.assert_not_called()

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


class TestActivityContextSendConversationRef:
    """Passing a conversation reference to ActivityContext.send() is deprecated but still works."""

    @pytest.mark.asyncio
    async def test_send_with_conversation_ref_warns_and_sends_to_that_conversation(self) -> None:
        ctx, _ = _create_activity_context()
        other_ref = ConversationReference(
            bot=Account(id="bot-id", name="Test Bot"),
            conversation=ConversationAccount(id="other-conversation"),
            channel_id="msteams",
            service_url="https://service.example",
        )

        with pytest.warns(
            DeprecationWarning,
            match=(
                r"Use `App.send\(\)` to send to a different conversation\. "
                r"`App.send\(\)` uses the service URL the app is configured with unless `service_url` is passed, "
                r"unlike the context methods, which use the service URL of the conversation reference "
                r"\(by default, the inbound activity's\)\."
            ),
        ):
            await ctx.send("Hello", other_ref)

        ctx.api.conversations.activities.assert_called_once_with("other-conversation")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("args", [(), (None,)], ids=["omitted", "explicit-none"])
    async def test_send_without_conversation_ref_does_not_warn(self, args: tuple[None, ...]) -> None:
        ctx, _ = _create_activity_context()

        with warnings.catch_warnings():
            warnings.simplefilter("error", DeprecationWarning)
            await ctx.send("Hello", *args)

        ctx.api.conversations.activities.assert_called_once_with("test-conversation")


CHAT_ID = "19:user_bot@unq.gbl.spaces"
CHANNEL_ID = "19:channel@thread.tacv2"


def _inbound_message(
    activity_id: str,
    channel_data: dict[str, Any],
    conversation_id: str = "test-conversation",
    conversation_type: str | None = None,
):
    return MessageActivity(
        id=activity_id,
        text="Incoming message",
        from_=Account(id="user-id", name="Test User"),
        recipient=Account(id="bot-id", name="Test Bot"),
        conversation=ConversationAccount(id=conversation_id, conversation_type=conversation_type),
        channel_data=ChannelData.model_validate(channel_data),
    )


def _context_with_reply_chain_methods(activity: Any) -> ActivityContext[Any]:
    ctx, _ = _create_activity_context(activity=activity)
    ctx.api.conversations._create_reply_chain_activity = AsyncMock(
        return_value=SentActivity(id="reply-id", activity_params=MessageActivityInput(text="sent"))
    )
    ctx.api.conversations._create_targeted_reply_chain_activity = AsyncMock(
        return_value=SentActivity(id="targeted-reply-id", activity_params=MessageActivityInput(text="sent"))
    )
    return ctx


class TestActivityContextReplyChainPlacement:
    """The default placement of a send reads the reply chain from the inbound payload."""

    @pytest.mark.asyncio
    async def test_replies_in_the_reply_chain_when_the_inbound_is_inside_one(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )

        result = await ctx.send("hi")

        assert result.id == "reply-id"
        reply = ctx.api.conversations._create_reply_chain_activity
        reply.assert_called_once()
        assert reply.call_args.args[:2] == (CHAT_ID, "root-1")
        sent = reply.call_args.args[2]
        assert sent.text == "hi"
        assert sent.conversation.id == CHAT_ID
        ctx.api.conversations.create_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_to_the_inbound_conversation_in_a_group_chat_even_when_the_payload_has_both_ids(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}},
                conversation_type="groupChat",
            )
        )

        await ctx.send("hi")

        ctx.api.conversations.create_activity.assert_called_once()
        assert ctx.api.conversations.create_activity.call_args.args[0] == "test-conversation"
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_to_the_inbound_conversation_in_a_meeting_chat_even_when_the_payload_has_both_ids(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}, "meeting": {"id": "meeting-1"}},
                conversation_type="groupChat",
            )
        )

        await ctx.send("hi")

        ctx.api.conversations.create_activity.assert_called_once()
        assert ctx.api.conversations.create_activity.call_args.args[0] == "test-conversation"
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_places_a_reply_in_a_personal_chat(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}},
                conversation_type="personal",
            )
        )

        await ctx.send("hi")

        assert ctx.api.conversations._create_reply_chain_activity.call_args.args[:2] == (CHAT_ID, "root-1")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_code", [400, 404])
    async def test_does_not_fall_back_to_the_inbound_conversation_in_a_chat(self, status_code: int) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}},
                conversation_type="personal",
            )
        )
        ctx.api.conversations._create_reply_chain_activity = AsyncMock(side_effect=_http_status_error(status_code))

        with pytest.raises(HTTPStatusError):
            await ctx.send("hi")

        ctx.api.conversations._create_reply_chain_activity.assert_called_once()
        ctx.api.conversations.create_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_the_stream_in_the_reply_chain_when_the_inbound_is_inside_one_in_a_personal_chat(
        self,
    ) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}},
                conversation_type="personal",
            )
        )

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as http_stream:
            assert ctx.stream is http_stream.return_value

        http_stream.assert_called_once_with(
            ctx.api, ctx.conversation_ref, StreamOptions(StreamReplyChain(CHAT_ID, "root-1"))
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("activity_id", ["root-1", "reply-2"], ids=["root-post", "thread-reply"])
    async def test_creates_the_stream_in_the_reply_chain_of_the_thread_in_a_channel(self, activity_id: str) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                activity_id,
                {"channel": {"id": CHANNEL_ID}, "replyChain": {"id": "root-1"}},
                conversation_type="channel",
            )
        )

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as http_stream:
            assert ctx.stream is http_stream.return_value

        http_stream.assert_called_once_with(
            ctx.api, ctx.conversation_ref, StreamOptions(StreamReplyChain(CHANNEL_ID, "root-1"))
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("activity_id", "channel_data", "conversation_type"),
        [
            ("root-1", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}}, "personal"),
            ("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}}, "groupChat"),
            (
                "reply-2",
                {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}, "meeting": {"id": "meeting-1"}},
                "groupChat",
            ),
            ("m-1", {"chat": {"id": CHAT_ID}}, "personal"),
        ],
        ids=["top-level", "group-chat", "meeting-chat", "no-reply-chain"],
    )
    async def test_creates_the_stream_without_a_reply_chain(self, activity_id, channel_data, conversation_type) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message(activity_id, channel_data, conversation_type=conversation_type)
        )

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as http_stream:
            assert ctx.stream is http_stream.return_value

        http_stream.assert_called_once_with(ctx.api, ctx.conversation_ref, None)

    @pytest.mark.asyncio
    async def test_keeps_the_inbound_agentic_user_when_replying_in_the_reply_chain(self) -> None:
        recipient = Account(
            id="bot-id",
            name="Test Bot",
            agentic_app_blueprint_id="blueprint-id",
            agentic_app_id="agentic-app-id",
            agentic_user_id="agentic-user-id",
            tenant_id="tenant-id",
        )
        inbound = _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}}).model_copy(
            update={"recipient": recipient}
        )
        ctx = _context_with_reply_chain_methods(inbound)

        await ctx.send("hi")

        assert recipient.agentic_identity is not None
        ctx.api.clone.assert_called_once_with(
            service_url=ctx.conversation_ref.service_url,
            agentic_identity=recipient.agentic_identity,
        )
        ctx.api.conversations._create_reply_chain_activity.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_to_the_inbound_conversation_for_a_top_level_message(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("root-1", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )

        await ctx.send("hi")

        ctx.api.conversations.create_activity.assert_called_once()
        assert ctx.api.conversations.create_activity.call_args.args[0] == "test-conversation"
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_to_the_inbound_conversation_when_the_payload_has_no_reply_chain(self) -> None:
        ctx = _context_with_reply_chain_methods(_inbound_message("m-1", {"chat": {"id": CHAT_ID}}))

        await ctx.send("hi")

        assert ctx.api.conversations.create_activity.call_args.args[0] == "test-conversation"
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_to_the_inbound_conversation_when_the_chat_id_is_missing(self) -> None:
        ctx = _context_with_reply_chain_methods(_inbound_message("reply-2", {"replyChain": {"id": "root-1"}}))

        await ctx.send("hi")

        assert ctx.api.conversations.create_activity.call_args.args[0] == "test-conversation"
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("activity_id", "channel_data"),
        [
            ("reply-2", {"channel": {"id": CHANNEL_ID}}),
            ("reply-2", {"replyChain": {"id": "root-1"}}),
        ],
        ids=["no-reply-chain", "no-channel-id"],
    )
    async def test_sends_to_the_inbound_conversation_in_a_channel_when_an_id_is_missing(
        self, activity_id, channel_data
    ) -> None:
        suffixed = f"{CHANNEL_ID};messageid=root-1"
        ctx = _context_with_reply_chain_methods(
            _inbound_message(activity_id, channel_data, suffixed, conversation_type="channel")
        )
        ctx.conversation_ref.conversation.id = suffixed

        await ctx.send("hi")

        ctx.api.conversations.create_activity.assert_called_once()
        assert ctx.api.conversations.create_activity.call_args.args[0] == suffixed
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("activity_id", ["root-1", "reply-2"], ids=["root-post", "thread-reply"])
    async def test_replies_in_the_reply_chain_of_the_thread_in_a_channel(self, activity_id: str) -> None:
        suffixed = f"{CHANNEL_ID};messageid=root-1"
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                activity_id,
                {"channel": {"id": CHANNEL_ID}, "replyChain": {"id": "root-1"}},
                suffixed,
                conversation_type="channel",
            )
        )

        await ctx.send("hi")

        reply = ctx.api.conversations._create_reply_chain_activity
        reply.assert_called_once()
        assert reply.call_args.args[:2] == (CHANNEL_ID, "root-1")
        assert reply.call_args.args[2].conversation.id == CHANNEL_ID
        ctx.api.conversations.create_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_sends_to_the_inbound_conversation_when_the_reply_chain_route_is_not_found_in_a_channel(
        self,
    ) -> None:
        suffixed = f"{CHANNEL_ID};messageid=root-1"
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"channel": {"id": CHANNEL_ID}, "replyChain": {"id": "root-1"}},
                suffixed,
                conversation_type="channel",
            )
        )
        ctx.conversation_ref.conversation.id = suffixed
        ctx.api.conversations._create_reply_chain_activity = AsyncMock(side_effect=_http_status_error(404))

        result = await ctx.send("hi")

        ctx.api.conversations._create_reply_chain_activity.assert_called_once()
        ctx.api.conversations.create_activity.assert_called_once()
        conversation_id, sent = ctx.api.conversations.create_activity.call_args.args
        assert conversation_id == suffixed
        assert sent.conversation.id == suffixed
        assert result.id == "sent-activity-id"

    @pytest.mark.asyncio
    async def test_does_not_fall_back_in_a_channel_for_an_error_other_than_a_missing_route(self) -> None:
        suffixed = f"{CHANNEL_ID};messageid=root-1"
        ctx = _context_with_reply_chain_methods(
            _inbound_message(
                "reply-2",
                {"channel": {"id": CHANNEL_ID}, "replyChain": {"id": "root-1"}},
                suffixed,
                conversation_type="channel",
            )
        )
        ctx.api.conversations._create_reply_chain_activity = AsyncMock(side_effect=_http_status_error(400))

        with pytest.raises(HTTPStatusError):
            await ctx.send("hi")

        ctx.api.conversations.create_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_place_an_update_of_an_existing_message(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )
        edited = MessageActivityInput(text="edited")
        edited.id = "existing-1"

        await ctx.send(edited)

        ctx.api.conversations.update_activity.assert_called_once()
        assert ctx.api.conversations.update_activity.call_args.args[:2] == ("test-conversation", "existing-1")
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_place_a_typing_activity(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )

        await ctx.send(TypingActivityInput())

        ctx.api.conversations.create_activity.assert_called_once()
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_does_not_place_a_send_to_a_different_conversation(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )
        other_ref = ConversationReference(
            bot=Account(id="bot-id", name="Test Bot"),
            conversation=ConversationAccount(id="other-conversation"),
            channel_id="msteams",
            service_url="https://service.example",
        )

        with pytest.warns(DeprecationWarning):
            await ctx.send("hi", other_ref)

        assert ctx.api.conversations.create_activity.call_args.args[0] == "other-conversation"
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_places_a_send_that_names_the_inbound_conversation(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )

        with pytest.warns(DeprecationWarning):
            await ctx.send("hi", ctx.conversation_ref)

        assert ctx.api.conversations._create_reply_chain_activity.call_args.args[:2] == (CHAT_ID, "root-1")

    @pytest.mark.asyncio
    async def test_replies_with_a_targeted_activity_in_the_reply_chain(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )
        activity = MessageActivityInput(text="hi").with_recipient(
            Account(id="user-id", name="Test User", role="user"), is_targeted=True
        )

        result = await ctx.send(activity)

        assert result.id == "targeted-reply-id"
        assert ctx.api.conversations._create_targeted_reply_chain_activity.call_args.args[:2] == (CHAT_ID, "root-1")
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()

    @pytest.mark.asyncio
    async def test_keeps_the_quote_when_replying_inside_a_reply_chain(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )

        await ctx.reply("hi")

        reply = ctx.api.conversations._create_reply_chain_activity
        assert reply.call_args.args[:2] == (CHAT_ID, "root-1")
        sent = reply.call_args.args[2]
        assert sent.entities is not None
        assert any(isinstance(entity, QuotedReplyEntity) for entity in sent.entities)

    @pytest.mark.asyncio
    async def test_does_not_modify_the_conversation_reference_of_the_context(self) -> None:
        ctx = _context_with_reply_chain_methods(
            _inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )

        await ctx.send("hi")

        assert ctx.conversation_ref.conversation.id == "test-conversation"


def _shape(
    type_: str,
    activity_id: str = "f:client-id",
    reply_to_id: str | None = None,
    value: Any = None,
    channel_data: dict[str, Any] | None = None,
    conversation_type: str = "personal",
) -> Any:
    conversation_id = f"{CHANNEL_ID};messageid=100" if conversation_type == "channel" else "a:encrypted-conversation"
    return SimpleNamespace(
        type=type_,
        id=activity_id,
        reply_to_id=reply_to_id,
        value=value,
        text="Incoming",
        from_=Account(id="user-id", name="Test User"),
        recipient=Account(id="bot-id", name="Test Bot"),
        conversation=ConversationAccount(id=conversation_id, conversation_type=conversation_type),
        channel_data=ChannelData.model_validate(channel_data or {}),
    )


def _chat_data(reply_chain_id: str, **extra: Any) -> dict[str, Any]:
    return {"chat": {"id": CHAT_ID}, "replyChain": {"id": reply_chain_id}, **extra}


_FROM_CARD = {"source": {"name": "message"}}
_THREAD_SHAPES = [
    pytest.param(dict(type_="message", reply_to_id="{id}"), _FROM_CARD, id="message-from-card"),
    pytest.param(dict(type_="invoke", reply_to_id="{id}"), {}, id="card-invoke"),
    pytest.param(
        dict(type_="invoke", value=SimpleNamespace(message_payload=SimpleNamespace(id="{id}"))), {}, id="message-action"
    ),
    pytest.param(dict(type_="messageReaction", activity_id="{id}"), {}, id="reaction"),
    pytest.param(dict(type_="messageUpdate", activity_id="{id}"), {}, id="edit"),
    pytest.param(dict(type_="messageDelete", activity_id="{id}"), {}, id="delete"),
]


def _fill(shape: dict[str, Any], message_id: str) -> dict[str, Any]:
    filled: dict[str, Any] = {}
    for key, value in shape.items():
        if value == "{id}":
            filled[key] = message_id
        elif isinstance(value, SimpleNamespace):
            filled[key] = SimpleNamespace(message_payload=SimpleNamespace(id=message_id))
        else:
            filled[key] = value
    return filled


class TestActivityContextReplyChainPlacementByShape:
    """The placement of a send follows the id of the message the inbound activity acts on."""

    @staticmethod
    async def _send(activity: Any) -> ActivityContext[Any]:
        ctx = _context_with_reply_chain_methods(activity)
        ctx.conversation_ref.conversation.id = activity.conversation.id
        await ctx.send("hi")
        return ctx

    @staticmethod
    def _assert_in_thread(ctx: ActivityContext[Any]) -> None:
        reply = ctx.api.conversations._create_reply_chain_activity
        reply.assert_called_once()
        assert reply.call_args.args[:2] == (CHAT_ID, "100")
        ctx.api.conversations.create_activity.assert_not_called()

    @staticmethod
    def _assert_in_inbound_conversation(
        ctx: ActivityContext[Any], conversation_id: str = "a:encrypted-conversation"
    ) -> None:
        ctx.api.conversations._create_reply_chain_activity.assert_not_called()
        ctx.api.conversations.create_activity.assert_called_once()
        assert ctx.api.conversations.create_activity.call_args.args[0] == conversation_id

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("shape", "extra"), _THREAD_SHAPES)
    async def test_replies_in_the_thread_for_a_message_inside_a_thread(self, shape, extra) -> None:
        ctx = await self._send(_shape(**_fill(shape, "105"), channel_data=_chat_data("100", **extra)))

        self._assert_in_thread(ctx)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("shape", "extra"), _THREAD_SHAPES)
    async def test_sends_to_the_inbound_conversation_for_a_top_level_message(self, shape, extra) -> None:
        ctx = await self._send(_shape(**_fill(shape, "100"), channel_data=_chat_data("100", **extra)))

        self._assert_in_inbound_conversation(ctx)

    @pytest.mark.asyncio
    async def test_compares_a_message_action_with_the_message_payload_id_not_the_reply_id(self) -> None:
        value = SimpleNamespace(message_payload=SimpleNamespace(id="105"))
        ctx = await self._send(_shape("invoke", reply_to_id="100", value=value, channel_data=_chat_data("100")))

        self._assert_in_thread(ctx)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("type_", ["message", "invoke"])
    @pytest.mark.parametrize(
        "reply_to_id",
        ["1:abc", "0", "12a", "", "١٢٣"],
        ids=["encrypted", "zero", "other-characters", "empty", "non-ascii-digits"],
    )
    async def test_does_not_place_a_card_message_or_invoke_with_a_replyToId_that_is_not_a_plain_number(
        self, type_, reply_to_id
    ) -> None:
        extra = _FROM_CARD if type_ == "message" else {}
        ctx = await self._send(_shape(type_, reply_to_id=reply_to_id, channel_data=_chat_data("100", **extra)))

        self._assert_in_inbound_conversation(ctx)

    @pytest.mark.asyncio
    async def test_does_not_place_a_card_message_without_a_replyToId(self) -> None:
        ctx = await self._send(_shape("message", channel_data=_chat_data("100", **_FROM_CARD)))

        self._assert_in_inbound_conversation(ctx)

    @pytest.mark.asyncio
    async def test_places_an_invoke_that_is_not_tied_to_a_message_when_the_payload_has_a_reply_chain_id(self) -> None:
        ctx = await self._send(_shape("invoke", channel_data=_chat_data("100")))

        self._assert_in_thread(ctx)

    @pytest.mark.asyncio
    async def test_does_not_place_an_invoke_that_is_not_tied_to_a_message_without_a_reply_chain_id(self) -> None:
        ctx = await self._send(_shape("invoke", channel_data={"chat": {"id": CHAT_ID}}))

        self._assert_in_inbound_conversation(ctx)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("conversation_type", ["personal", "channel"])
    async def test_does_not_place_a_message_when_the_reply_chain_id_is_empty(self, conversation_type) -> None:
        scope = {"channel": {"id": CHANNEL_ID}} if conversation_type == "channel" else {"chat": {"id": CHAT_ID}}
        ctx = await self._send(
            _shape(
                "message",
                activity_id="105",
                conversation_type=conversation_type,
                channel_data={**scope, "replyChain": {"id": ""}},
            )
        )

        self._assert_in_inbound_conversation(
            ctx, f"{CHANNEL_ID};messageid=100" if conversation_type == "channel" else "a:encrypted-conversation"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("type_", ["conversationUpdate", "installationUpdate", "event", "typing"])
    async def test_never_places_other_activities(self, type_) -> None:
        ctx = await self._send(_shape(type_, activity_id="105", channel_data=_chat_data("100")))

        self._assert_in_inbound_conversation(ctx)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("type_", ["message", "invoke", "messageReaction"])
    async def test_does_not_place_anything_in_a_group_chat(self, type_) -> None:
        ctx = await self._send(
            _shape(
                type_,
                activity_id="105",
                reply_to_id="105",
                conversation_type="groupChat",
                channel_data=_chat_data("100"),
            )
        )

        self._assert_in_inbound_conversation(ctx)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("type_", ["invoke", "messageReaction"])
    async def test_does_not_place_an_invoke_or_reaction_in_a_channel(self, type_) -> None:
        ctx = await self._send(
            _shape(
                type_,
                activity_id="105",
                reply_to_id="105",
                conversation_type="channel",
                channel_data={"channel": {"id": CHANNEL_ID}, "replyChain": {"id": "100"}},
            )
        )

        self._assert_in_inbound_conversation(ctx, f"{CHANNEL_ID};messageid=100")

    @pytest.mark.asyncio
    async def test_places_a_card_message_in_a_channel_in_the_reply_chain_of_the_thread(self) -> None:
        ctx = await self._send(
            _shape(
                "message",
                reply_to_id="105",
                conversation_type="channel",
                channel_data={"channel": {"id": CHANNEL_ID}, "replyChain": {"id": "100"}, **_FROM_CARD},
            )
        )

        reply = ctx.api.conversations._create_reply_chain_activity
        reply.assert_called_once()
        assert reply.call_args.args[:2] == (CHANNEL_ID, "100")


def _payload(fields: dict[str, Any], reply_chain_id: str, source: str | None = None) -> dict[str, Any]:
    channel_data: dict[str, Any] = {"chat": {"id": CHAT_ID}, "replyChain": {"id": reply_chain_id}}
    if source:
        channel_data["source"] = {"name": source}
    return {
        "channelId": "msteams",
        "serviceUrl": "https://service.url",
        "from": {"id": "user-1", "name": "Test User"},
        "recipient": {"id": "bot-1", "name": "Test Bot"},
        "conversation": {"id": "a:opaque-conversation", "conversationType": "personal"},
        "channelData": channel_data,
        **fields,
    }


class TestActivityContextReplyChainPlacementFromPayloads:
    """The placement of a send reads the shapes of the payloads Teams sends, parsed by the SDK."""

    @staticmethod
    def _payloads(message_id: str, root_id: str) -> dict[str, dict[str, Any]]:
        return {
            "messageBack": _payload(
                {
                    "type": "message",
                    "id": "f:75fdb71e-3aeb-8ff2-8bdf-e1709d492142",
                    "replyToId": message_id,
                    "value": {"type": "messageBack", "text": "capture mb", "value": {"probe": "mb"}},
                },
                root_id,
                "message",
            ),
            "adaptiveCard/action": _payload(
                {
                    "type": "invoke",
                    "name": "adaptiveCard/action",
                    "id": "f:ec156ed9-f382-40ee-5384-8e38f066fee2",
                    "replyToId": message_id,
                    "value": {"action": {"type": "Action.Execute", "verb": "capture_execute", "data": {}}},
                },
                root_id,
                "message",
            ),
            "message action": _payload(
                {
                    "type": "invoke",
                    "name": "composeExtension/submitAction",
                    "id": "f:fa6ab590-4432-37f6-4cf9-93a20a055fb4",
                    "value": {
                        "commandId": "getMessageDetails",
                        "commandContext": "message",
                        "messagePayload": {"id": message_id},
                    },
                },
                root_id,
                "compose",
            ),
            "reaction": _payload(
                {
                    "type": "messageReaction",
                    "id": message_id,
                    "replyToId": message_id,
                    "reactionsAdded": [{"type": "like"}],
                },
                root_id,
            ),
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", ["messageBack", "adaptiveCard/action", "message action", "reaction"])
    async def test_replies_in_the_thread_for_a_message_inside_a_thread(self, shape: str) -> None:
        activity = TypeAdapter(Activity).validate_python(self._payloads("1793230385713", "1793230314269")[shape])
        ctx = _context_with_reply_chain_methods(activity)

        await ctx.send("hi")

        reply = ctx.api.conversations._create_reply_chain_activity
        reply.assert_called_once()
        assert reply.call_args.args[:2] == (CHAT_ID, "1793230314269")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("shape", ["messageBack", "adaptiveCard/action", "message action", "reaction"])
    async def test_sends_to_the_inbound_conversation_for_a_top_level_message(self, shape: str) -> None:
        activity = TypeAdapter(Activity).validate_python(self._payloads("1793230432295", "1793230432295")[shape])
        ctx = _context_with_reply_chain_methods(activity)
        ctx.conversation_ref.conversation.id = "a:opaque-conversation"

        await ctx.send("hi")

        ctx.api.conversations._create_reply_chain_activity.assert_not_called()
        ctx.api.conversations.create_activity.assert_called_once()


_ABSENT = object()
_EXECUTE_VALUE = {"action": {"type": "Action.Execute", "verb": "capture_execute", "data": {}}}
_FROM_CARD_SOURCE = {"name": "message"}
_COMPOSE_SOURCE = {"name": "compose"}


def _message_action(payload_id: Any, reply_to_id: Any = _ABSENT) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "type": "invoke",
        "name": "composeExtension/submitAction",
        "value": {"commandId": "c", "commandContext": "message", "messagePayload": {"id": payload_id}},
    }
    if reply_to_id is not _ABSENT:
        fields["replyToId"] = reply_to_id
    return fields


def _untyped_message_action(payload_id: Any, reply_to_id: Any) -> dict[str, Any]:
    """A `selectItem` invoke keeps its value as a dict, so a null `messagePayload.id` reaches the handler.

    The typed `messageAction` value requires a string id, so the SDK rejects a null id there.
    """
    return {
        "type": "invoke",
        "name": "composeExtension/selectItem",
        "replyToId": reply_to_id,
        "value": {"messagePayload": {"id": payload_id}},
    }


def _null_and_empty_payload(
    fields: dict[str, Any], source: Any = _ABSENT, reply_chain: Optional[str] = "100"
) -> dict[str, Any]:
    payload = _payload({"id": "f:1", **fields}, reply_chain or "100")
    if reply_chain is None:
        del payload["channelData"]["replyChain"]
    if source is not _ABSENT:
        payload["channelData"]["source"] = source
    return payload


# (activity fields, source, replyChain.id, expected). The chat reply chain is 100 and the message is 105 unless stated.
_NULL_AND_EMPTY_CASES: list[Any] = [
    pytest.param({"type": "message", "id": "105"}, _ABSENT, "100", True, id="1-message-without-source"),
    pytest.param({"type": "message", "id": "105"}, None, "100", True, id="2-message-source-null"),
    pytest.param({"type": "message", "id": "100"}, None, "100", False, id="3-root-message-source-null"),
    pytest.param({"type": "message", "id": "100"}, {}, "100", False, id="3b-root-message-source-empty-object"),
    pytest.param(
        {"type": "message", "id": "105", "replyToId": "100"}, {}, "100", True, id="4-message-source-empty-object"
    ),
    pytest.param(
        {"type": "message", "id": "105", "replyToId": "100"},
        {"name": ""},
        "100",
        True,
        id="4b-message-source-name-empty-string",
    ),
    pytest.param(
        {"type": "message", "id": "105", "replyToId": "100"},
        {"foo": 1},
        "100",
        True,
        id="4c-message-source-unknown-key-only",
    ),
    pytest.param(
        {"type": "message", "id": "105", "replyToId": "100"},
        {"name": 5},
        "100",
        True,
        id="4d-message-source-name-not-a-string",
    ),
    pytest.param(
        {"type": "message", "id": "100", "replyToId": "99"},
        {"name": ""},
        "100",
        False,
        id="4e-root-message-source-name-empty-string",
    ),
    pytest.param(
        {"type": "message", "id": "105", "replyToId": "105"}, {}, "100", True, id="5-message-source-empty-object-other"
    ),
    pytest.param(
        {"type": "message", "id": "f:1", "replyToId": "100"}, _FROM_CARD_SOURCE, "100", False, id="6-card-top-level"
    ),
    pytest.param(
        {"type": "message", "id": "f:1", "replyToId": "105"}, _FROM_CARD_SOURCE, "100", True, id="7-card-in-thread"
    ),
    pytest.param(
        {"type": "invoke", "name": "task/fetch", "value": {}}, _ABSENT, "100", True, id="8-invoke-without-reply-to-id"
    ),
    pytest.param(
        {"type": "invoke", "name": "task/fetch", "value": {}}, _ABSENT, None, False, id="9-invoke-without-reply-chain"
    ),
    pytest.param(
        {"type": "invoke", "name": "task/fetch", "replyToId": None, "value": {}},
        _ABSENT,
        "100",
        True,
        id="10-invoke-reply-to-id-null",
    ),
    pytest.param(
        {"type": "invoke", "name": "task/fetch", "replyToId": "", "value": {}},
        _ABSENT,
        "100",
        False,
        id="11-invoke-reply-to-id-empty",
    ),
    pytest.param(
        _untyped_message_action(None, "105"), _COMPOSE_SOURCE, "100", True, id="12-message-action-id-null-other"
    ),
    pytest.param(
        _untyped_message_action(None, "100"), _COMPOSE_SOURCE, "100", False, id="13-message-action-id-null-root"
    ),
    pytest.param(_message_action("", "105"), _COMPOSE_SOURCE, "100", False, id="14-message-action-id-empty"),
    pytest.param(_message_action("105"), _COMPOSE_SOURCE, "100", True, id="15-message-action-in-thread"),
    pytest.param(_message_action("100"), _COMPOSE_SOURCE, "100", False, id="16-message-action-top-level"),
    pytest.param(
        {"type": "invoke", "name": "adaptiveCard/action", "replyToId": "105", "value": _EXECUTE_VALUE},
        _FROM_CARD_SOURCE,
        "100",
        True,
        id="card-invoke-in-thread",
    ),
    pytest.param(
        {"type": "invoke", "name": "adaptiveCard/action", "replyToId": "100", "value": _EXECUTE_VALUE},
        _FROM_CARD_SOURCE,
        "100",
        False,
        id="card-invoke-top-level",
    ),
    pytest.param(
        {"type": "invoke", "name": "composeExtension/selectItem", "value": {"messagePayload": {"id": "105"}}},
        _COMPOSE_SOURCE,
        "100",
        True,
        id="untyped-value-payload-id-in-thread",
    ),
    pytest.param(
        {"type": "invoke", "name": "composeExtension/selectItem", "value": {"messagePayload": {"id": "100"}}},
        _COMPOSE_SOURCE,
        "100",
        False,
        id="untyped-value-payload-id-top-level",
    ),
    pytest.param(
        {"type": "invoke", "name": "composeExtension/selectItem", "value": {"messagePayload": {"id": ""}}},
        _COMPOSE_SOURCE,
        "100",
        False,
        id="untyped-value-payload-id-empty",
    ),
    pytest.param(
        {
            "type": "invoke",
            "name": "composeExtension/selectItem",
            "replyToId": "100",
            "value": {"messagePayload": {"id": 100}},
        },
        _COMPOSE_SOURCE,
        "100",
        False,
        id="untyped-value-payload-id-number-with-reply-to-id",
    ),
    pytest.param(
        {"type": "invoke", "name": "composeExtension/selectItem", "value": {"messagePayload": {"id": 99}}},
        _COMPOSE_SOURCE,
        "100",
        True,
        id="untyped-value-payload-id-not-a-string",
    ),
]


class TestActivityContextReplyChainPlacementFromNullAndEmptyFields:
    """Null and empty fields in a parsed payload classify the same way for sends and for streams."""

    @staticmethod
    def _activity(fields: dict[str, Any], source: Any, reply_chain: Optional[str]) -> Any:
        # The model rejects a `source.name` that is not a string, so such a payload is built past the validation.
        wrong_type = isinstance(source, dict) and not isinstance(source.get("name", ""), (str, type(None)))
        payload = _null_and_empty_payload(fields, _ABSENT if wrong_type else source, reply_chain)
        activity = TypeAdapter(Activity).validate_python(payload)
        if wrong_type:
            activity.channel_data.source = SourceInfo.model_construct(**source)
        return activity

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("fields", "source", "reply_chain", "in_thread"), _NULL_AND_EMPTY_CASES)
    async def test_send_places_the_response_when_the_activity_is_inside_a_thread(
        self, fields: dict[str, Any], source: Any, reply_chain: Optional[str], in_thread: bool
    ) -> None:
        ctx = _context_with_reply_chain_methods(self._activity(fields, source, reply_chain))
        ctx.conversation_ref.conversation.id = "a:opaque-conversation"

        await ctx.send("hi")

        reply = ctx.api.conversations._create_reply_chain_activity
        if in_thread:
            reply.assert_called_once()
            assert reply.call_args.args[:2] == (CHAT_ID, "100")
            ctx.api.conversations.create_activity.assert_not_called()
        else:
            reply.assert_not_called()
            ctx.api.conversations.create_activity.assert_called_once()

    @pytest.mark.parametrize(("fields", "source", "reply_chain", "in_thread"), _NULL_AND_EMPTY_CASES)
    def test_stream_starts_in_the_reply_chain_when_the_activity_is_inside_a_thread(
        self, fields: dict[str, Any], source: Any, reply_chain: Optional[str], in_thread: bool
    ) -> None:
        ctx = _context_with_reply_chain_methods(self._activity(fields, source, reply_chain))

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as http_stream:
            assert ctx.stream is http_stream.return_value

        http_stream.assert_called_once_with(
            ctx.api,
            ctx.conversation_ref,
            StreamOptions(StreamReplyChain(CHAT_ID, "100")) if in_thread else None,
        )


class TestActivityContextReplyChainPlacementWithBlankIds:
    """A blank id counts as missing, so the send goes to the inbound conversation and nothing throws."""

    @staticmethod
    def _activity(conversation_type: str, scope_id: str, reply_chain_id: str) -> Any:
        scope = "channel" if conversation_type == "channel" else "chat"
        conversation_id = f"{CHANNEL_ID};messageid=100" if conversation_type == "channel" else "a:opaque-conversation"
        return _inbound_message(
            "105",
            {scope: {"id": scope_id}, "replyChain": {"id": reply_chain_id}},
            conversation_id=conversation_id,
            conversation_type=conversation_type,
        )

    @pytest.mark.parametrize(
        ("conversation_type", "scope_id", "reply_chain_id"),
        [
            ("personal", " ", "100"),
            ("personal", "\t\n", "100"),
            ("personal", CHAT_ID, " "),
            ("personal", CHAT_ID, "\t"),
            ("channel", " ", "100"),
            ("channel", CHANNEL_ID, " "),
            ("channel", CHANNEL_ID, "\n"),
        ],
        ids=[
            "chat-id-space",
            "chat-id-tab-newline",
            "chain-space",
            "chain-tab",
            "channel-id",
            "chain-in-channel",
            "chain-newline",
        ],
    )
    @pytest.mark.asyncio
    async def test_send_goes_to_the_inbound_conversation(self, conversation_type, scope_id, reply_chain_id) -> None:
        activity = self._activity(conversation_type, scope_id, reply_chain_id)
        ctx = _context_with_reply_chain_methods(activity)
        ctx.conversation_ref.conversation.id = activity.conversation.id

        await ctx.send("hi")

        ctx.api.conversations._create_reply_chain_activity.assert_not_called()
        ctx.api.conversations.create_activity.assert_called_once()
        assert ctx.api.conversations.create_activity.call_args.args[0] == activity.conversation.id

    @pytest.mark.parametrize(
        ("conversation_type", "scope_id", "reply_chain_id"),
        [
            ("personal", " ", "100"),
            ("personal", CHAT_ID, " "),
            ("channel", " ", "100"),
            ("channel", CHANNEL_ID, " "),
        ],
        ids=["chat-id", "chain-in-chat", "channel-id", "chain-in-channel"],
    )
    def test_stream_starts_in_the_inbound_conversation(self, conversation_type, scope_id, reply_chain_id) -> None:
        ctx = _context_with_reply_chain_methods(self._activity(conversation_type, scope_id, reply_chain_id))

        with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as http_stream:
            assert ctx.stream is http_stream.return_value

        http_stream.assert_called_once_with(ctx.api, ctx.conversation_ref, None)

    @pytest.mark.asyncio
    async def test_a_padded_id_that_is_not_blank_is_still_placed(self) -> None:
        activity = self._activity("personal", CHAT_ID, "100")
        ctx = _context_with_reply_chain_methods(activity)

        await ctx.send("hi")

        ctx.api.conversations._create_reply_chain_activity.assert_called_once()


def _real_conversations() -> Any:
    """A real `ConversationClient` whose HTTP layer is replaced, so that its public methods run for real."""
    conversations = ConversationClient("https://service.example", Client(ClientOptions()))
    sent = SentActivity(id="sent-id", activity_params=MessageActivityInput(text="sent"))
    activities = MagicMock()
    for name in ("create", "create_targeted", "create_reply_chain", "create_targeted_reply_chain"):
        setattr(activities, name, AsyncMock(return_value=sent))
    conversations._activities_client = activities  # pyright: ignore[reportPrivateUsage]
    return conversations


class TestActivityContextReplyChainPreviewWarning:
    """The SDK places responses through the reply chain without emitting the preview warning."""

    @staticmethod
    def _context() -> ActivityContext[Any]:
        ctx, _ = _create_activity_context(
            activity=_inbound_message("reply-2", {"chat": {"id": CHAT_ID}, "replyChain": {"id": "root-1"}})
        )
        ctx.api.conversations = _real_conversations()
        return ctx

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["send", "reply"])
    async def test_a_placed_response_does_not_emit_the_warning(self, method: str) -> None:
        ctx = self._context()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await getattr(ctx, method)("hi")

        ctx.api.conversations._activities_client.create_reply_chain.assert_called_once()
        assert [w for w in caught if issubclass(w.category, ExperimentalWarning)] == []

    @pytest.mark.asyncio
    async def test_a_placed_targeted_response_does_not_emit_the_warning(self) -> None:
        ctx = self._context()
        activity = MessageActivityInput(text="hi").with_recipient(Account(id="user-1", name="U"), is_targeted=True)

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            await ctx.send(activity)

        ctx.api.conversations._activities_client.create_targeted_reply_chain.assert_called_once()
        assert [w for w in caught if issubclass(w.category, ExperimentalWarning)] == []


_DISPATCH_ROOT_L1 = "1793230315283"
_DISPATCH_ROOT_L2 = "1793230314269"
_DISPATCH_CARD_L2 = "1793230387232"
_DISPATCH_CONVERSATION = "a:opaque-conversation"


def _dispatch_payload(
    name: str,
    value: dict[str, Any],
    source: str,
    reply_to_id: Optional[str] = None,
    reply_chain_id: Optional[str] = None,
    conversation_type: str = "personal",
    conversation_id: str = _DISPATCH_CONVERSATION,
    scope: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """The structure of a captured invoke. Ids are shortened and tokens are not part of the shape."""
    channel_data: dict[str, Any] = {"source": {"name": source}, **(scope or {"chat": {"id": CHAT_ID}})}
    if reply_chain_id is not None:
        channel_data["replyChain"] = {"id": reply_chain_id}
    payload: dict[str, Any] = {
        "type": "invoke",
        "name": name,
        "id": "f:2c1a7d0e-1a2b-4c3d-8e9f-0a1b2c3d4e5f",
        "channelId": "msteams",
        "serviceUrl": "https://service.url",
        "from": {"id": "user-1", "name": "Test User"},
        "recipient": {"id": "bot-1", "name": "Test Bot"},
        "conversation": {"id": conversation_id, "conversationType": conversation_type},
        "channelData": channel_data,
        "value": value,
    }
    if reply_to_id is not None:
        payload["replyToId"] = reply_to_id
    return payload


_FETCH_TASK_VALUE = {"commandId": "fetchDialog", "commandContext": "compose", "context": {"theme": "default"}}
_QUERY_VALUE = {
    "commandId": "searchQuery",
    "parameters": [{"name": "searchQuery", "value": "q"}],
    "queryOptions": {"count": 25, "skip": 0},
}
_TASK_FETCH_VALUE = {"data": {"dialog_id": "capture_dialog", "type": "task/fetch"}, "context": {"theme": "default"}}
_TASK_SUBMIT_VALUE = {"data": {"action": "capture_dialog"}, "context": {"theme": "default"}}
_FEEDBACK_VALUE = {"actionName": "feedback", "actionValue": {"reaction": "like", "feedback": '{"feedbackText":"fb"}'}}
_EXECUTE_ACTION_VALUE = {"action": {"type": "Action.Execute", "verb": "capture_execute", "data": {}}}


def _contextless(name: str, value: dict[str, Any], source: str, level: str) -> dict[str, Any]:
    return _dispatch_payload(name, value, source, reply_chain_id=None if level == "L1" else _DISPATCH_ROOT_L2)


def _from_card(name: str, value: dict[str, Any], source: str, level: str) -> dict[str, Any]:
    if level == "L1":
        return _dispatch_payload(name, value, source, _DISPATCH_ROOT_L1, _DISPATCH_ROOT_L1)
    return _dispatch_payload(name, value, source, _DISPATCH_CARD_L2, _DISPATCH_ROOT_L2)


# (handler registration, activity type, payload factory, name, value, source).
# The shapes are the captured L1 and L2 invokes. The L2 root differs from the L1 root, as in the captures.
_DISPATCH_SHAPES: list[Any] = [
    pytest.param(
        "on_message_ext_open",
        MessageExtensionFetchTaskInvokeActivity,
        _contextless,
        "composeExtension/fetchTask",
        _FETCH_TASK_VALUE,
        "compose",
        id="contextless-fetchTask",
    ),
    pytest.param(
        "on_message_ext_query",
        MessageExtensionQueryInvokeActivity,
        _contextless,
        "composeExtension/query",
        _QUERY_VALUE,
        "compose",
        id="contextless-query",
    ),
    pytest.param(
        "on_dialog_open",
        TaskFetchInvokeActivity,
        _from_card,
        "task/fetch",
        _TASK_FETCH_VALUE,
        "compose",
        id="task-fetch-from-card",
    ),
    pytest.param(
        "on_dialog_submit",
        TaskSubmitInvokeActivity,
        _from_card,
        "task/submit",
        _TASK_SUBMIT_VALUE,
        "compose",
        id="task-submit-from-card",
    ),
    pytest.param(
        "on_message_submit_feedback",
        MessageSubmitActionInvokeActivity,
        _from_card,
        "message/submitAction",
        _FEEDBACK_VALUE,
        "message",
        id="feedback",
    ),
]


class TestActivityContextReplyChainPlacementThroughDispatch:
    """An invoke goes through the real router and the real handler, and the handler sends or streams."""

    @staticmethod
    async def _dispatch(
        payload: dict[str, Any], register: str, activity_type: Any, action: str = "send"
    ) -> tuple[Any, list[Any]]:
        app = App(storage=MagicMock(), client_id="test-client-id", client_secret="test-secret")
        calls: list[Any] = []
        sent = SentActivity(id="sent-1", activity_params=MessageActivityInput(text="hi"))

        async def handler(ctx: ActivityContext[Any]) -> Any:
            calls.append(ctx.activity.name)
            if action == "send":
                await ctx.send("hi")
            else:
                _ = ctx.stream
            return None

        handler.__annotations__ = {"ctx": ActivityContext[activity_type]}
        getattr(app, register)(handler)
        core = CoreActivity.model_validate(payload)
        token = MagicMock(spec=TokenProtocol)
        token.service_url = "https://service.url"
        with patch("microsoft_teams.apps.app_process.ApiClient") as api_client:
            api = MagicMock()
            api.users.token.get = AsyncMock(side_effect=Exception("no token"))
            api.conversations.create_activity = AsyncMock(return_value=sent)
            api.conversations._create_reply_chain_activity = AsyncMock(return_value=sent)
            api.clone.return_value = api
            api_client.return_value = api
            with patch("microsoft_teams.apps.routing.activity_context.HttpStream") as http_stream:
                http_stream.return_value.close = AsyncMock(return_value=None)
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    await app.activity_processor.process_activity([], ActivityEvent(body=core, token=token))
        return (api, http_stream), calls

    @pytest.mark.asyncio
    @pytest.mark.parametrize("level", ["L1", "L2"])
    @pytest.mark.parametrize(("register", "activity_type", "factory", "name", "value", "source"), _DISPATCH_SHAPES)
    async def test_send_from_the_handler_is_placed_by_the_shape(
        self, register: str, activity_type: Any, factory: Any, name: str, value: dict[str, Any], source: str, level: str
    ) -> None:
        payload = factory(name, value, source, level)

        (api, _), calls = await self._dispatch(payload, register, activity_type)

        assert calls == [name]
        conversations = api.conversations
        if level == "L2":
            conversations._create_reply_chain_activity.assert_called_once()
            assert conversations._create_reply_chain_activity.call_args.args[:2] == (
                CHAT_ID,
                _DISPATCH_ROOT_L2,
            )
            conversations.create_activity.assert_not_called()
        else:
            conversations._create_reply_chain_activity.assert_not_called()
            conversations.create_activity.assert_called_once()
            assert conversations.create_activity.call_args.args[0] == _DISPATCH_CONVERSATION

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("conversation_type", "conversation_id", "scope"),
        [
            ("groupChat", "19:grp@thread.v2", {"chat": {"id": "19:grp@thread.v2"}}),
            ("channel", f"{CHANNEL_ID};messageid={_DISPATCH_ROOT_L2}", {"channel": {"id": CHANNEL_ID}}),
        ],
        ids=["group-chat", "channel"],
    )
    async def test_a_card_invoke_in_a_group_chat_or_a_channel_is_never_placed(
        self, conversation_type: str, conversation_id: str, scope: dict[str, Any]
    ) -> None:
        payload = _dispatch_payload(
            "adaptiveCard/action",
            _EXECUTE_ACTION_VALUE,
            "message",
            _DISPATCH_CARD_L2,
            _DISPATCH_ROOT_L2,
            conversation_type,
            conversation_id,
            scope,
        )

        (api, _), calls = await self._dispatch(payload, "on_card_action", AdaptiveCardInvokeActivity)

        assert calls == ["adaptiveCard/action"]
        api.conversations._create_reply_chain_activity.assert_not_called()
        api.conversations.create_activity.assert_called_once()
        assert api.conversations.create_activity.call_args.args[0] == conversation_id

    @pytest.mark.asyncio
    @pytest.mark.parametrize("level", ["L1", "L2"])
    async def test_a_stream_started_by_a_card_invoke_follows_the_same_rule(self, level: str) -> None:
        payload = _from_card("adaptiveCard/action", _EXECUTE_ACTION_VALUE, "message", level)

        (_, http_stream), calls = await self._dispatch(payload, "on_card_action", AdaptiveCardInvokeActivity, "stream")

        assert calls == ["adaptiveCard/action"]
        http_stream.assert_called_once()
        options = http_stream.call_args.args[2]
        assert options == (StreamOptions(StreamReplyChain(CHAT_ID, _DISPATCH_ROOT_L2)) if level == "L2" else None)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload_id", [None, 100], ids=["missing", "number"])
    async def test_a_message_action_without_a_string_payload_id_does_not_reach_the_handler(
        self, payload_id: Any
    ) -> None:
        message_payload: dict[str, Any] = {} if payload_id is None else {"id": payload_id}
        payload = _dispatch_payload(
            "composeExtension/submitAction",
            {"commandId": "c", "commandContext": "message", "messagePayload": message_payload},
            "compose",
            _DISPATCH_CARD_L2,
            _DISPATCH_ROOT_L2,
        )

        with pytest.raises(ValidationError, match="message_payload|messagePayload"):
            await self._dispatch(payload, "on_message_ext_submit", MessageExtensionSubmitActionInvokeActivity)


class TestActivityContextReply:
    """Tests for ActivityContext.reply()."""

    @pytest.mark.asyncio
    async def test_reply_with_string(self) -> None:
        """reply() with a plain string stamps a quotedReply entity and placeholder."""
        mock_activity = MagicMock()
        mock_activity.type = "message"
        mock_activity.id = "original-id"
        mock_activity.text = "Original message"
        mock_activity.channel_data = None

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
        mock_activity.channel_data = None

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
    """Tests for sign_out(connection_name=), get_user_token, and get_connection_status."""

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
    async def test_get_connection_status_returns_all_connections(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """get_connection_status makes a single call and returns the status list unfiltered."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        statuses = [MagicMock(), MagicMock()]
        ctx.api.users.get_token_status = AsyncMock(return_value=statuses)
        telemetry_calls, telemetry = _capture_oauth_operation(monkeypatch)

        result = await ctx.get_connection_status()

        assert result is statuses
        ctx.api.users.get_token_status.assert_awaited_once()
        params = ctx.api.users.get_token_status.call_args[0][0]
        assert params.include_filter is None
        assert params.user_id == "user-1"
        assert params.channel_id == "msteams"
        assert telemetry_calls == [("all", "connection_status")]
        assert telemetry.result == "operation_succeeded"

    @pytest.mark.asyncio
    async def test_get_connection_status_propagates_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Unlike get_user_token, get_connection_status lets service failures surface."""
        mock_activity = MagicMock()
        mock_activity.channel_id = "msteams"
        mock_activity.from_.id = "user-1"

        ctx, _ = _create_activity_context(activity=mock_activity)
        ctx.api.users.get_token_status = AsyncMock(side_effect=RuntimeError("service down"))
        telemetry_calls, telemetry = _capture_oauth_operation(monkeypatch)

        with pytest.raises(RuntimeError):
            await ctx.get_connection_status()
        assert telemetry_calls == [("all", "connection_status")]
        assert telemetry.result == "operation_failed"


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
    """get_connection_status corrects the bulk call for registered flows."""

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

        assert await ctx.get_connection_status() is statuses

    @pytest.mark.asyncio
    async def test_false_status_for_a_registered_flow_is_corrected(self) -> None:
        """The bulk call can lag a token that was just written.

        Red-green: without the per-flow lookup this reports has_token=False for a
        connection the user is demonstrably signed in to.
        """
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("graph", False)])
        ctx.api.users.get_token = AsyncMock(return_value=MagicMock(token="a-token"))

        result = await ctx.get_connection_status()

        assert [(s.connection_name, s.has_token) for s in result] == [("graph", True)]

    @pytest.mark.asyncio
    async def test_a_genuine_miss_stays_false(self) -> None:
        """A confirmed absence is not rewritten."""
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("graph", False)])
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(404))

        result = await ctx.get_connection_status()

        assert [(s.connection_name, s.has_token) for s in result] == [("graph", False)]

    @pytest.mark.asyncio
    async def test_a_registered_flow_missing_from_the_bulk_result_is_added(self) -> None:
        """The service only lists connections it knows; a flow may be absent."""
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("legacy", True)])
        ctx.api.users.get_token = AsyncMock(return_value=MagicMock(token="a-token"))

        result = await ctx.get_connection_status()

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

        result = await ctx.get_connection_status()

        assert result[0] is legacy
        assert probes == []

    @pytest.mark.asyncio
    async def test_registry_casing_is_matched_case_insensitively(self) -> None:
        """The service may echo a different casing than the app registered."""
        ctx = self._context(["Graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("GRAPH", False)])
        ctx.api.users.get_token = AsyncMock(return_value=MagicMock(token="a-token"))

        result = await ctx.get_connection_status()

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

        result = await ctx.get_connection_status()

        assert [s.connection_name for s in result] == ["a", "b", "c", "missing"]

    @pytest.mark.asyncio
    async def test_non_404_lookup_failure_propagates(self) -> None:
        """An outage during the correction is not silently reported as False."""
        ctx = self._context(["graph"])
        ctx.api.users.get_token_status = AsyncMock(return_value=[self._status("graph", False)])
        ctx.api.users.get_token = AsyncMock(side_effect=_http_status_error(503))

        with pytest.raises(HTTPStatusError):
            await ctx.get_connection_status()


class TestConnectionStatusRename:
    """``ctx.get_token_status`` was renamed to ``ctx.get_connection_status``."""

    def test_old_context_name_is_gone(self) -> None:
        """Renamed outright rather than aliased - the method was never released."""
        ctx, _ = _create_activity_context()

        assert not hasattr(ctx, "get_token_status")
        assert hasattr(ctx, "get_connection_status")

    def test_api_client_keeps_the_endpoint_name(self) -> None:
        """The API layer must keep its name; renaming both would undo the fix.

        ``api.users.get_token_status`` is the Token Service endpoint and returns
        the service answer verbatim, while ``ctx.get_connection_status`` adds the
        silent-SSO correction pass. One name for two behaviors was the problem.
        """
        from microsoft_teams.api.clients.user.client import UserClient

        assert hasattr(UserClient, "get_token_status")
        assert not hasattr(UserClient, "get_connection_status")
