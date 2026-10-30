"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import base64
import json
import logging
import warnings
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    List,
    NamedTuple,
    Optional,
    Sequence,
    TypeGuard,
    TypeVar,
    cast,
    overload,
)

from httpx import HTTPStatusError
from microsoft_teams.api import (
    Account,
    ActivityBase,
    ActivityParams,
    ApiClient,
    CardAction,
    CardActionType,
    ChannelData,
    ConversationReference,
    GetBotSignInResourceParams,
    GetUserTokenParams,
    GetUserTokenStatusParams,
    JsonWebToken,
    MessageActivity,
    MessageActivityInput,
    SentActivity,
    SignOutUserParams,
    TokenExchangeResource,
    TokenExchangeState,
    TokenPostResource,
    TokenStatus,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment
from microsoft_teams.api.models.attachment.card_attachment import (
    OAuthCardAttachment,
    card_attachment,
)
from microsoft_teams.api.models.oauth import OAuthCard
from microsoft_teams.cards import AdaptiveCard
from microsoft_teams.common import Storage
from microsoft_teams.common.experimental import experimental
from microsoft_teams.common.http.client_token import Token
from typing_extensions import deprecated

from ..activity_send import send_or_update_activity
from ..diagnostics._constants import (
    APP_OAUTH_ALL_CONNECTIONS,
    APP_OAUTH_OPERATIONS,
    APP_OAUTH_RESULTS,
)
from ..diagnostics._helpers import trace_oauth_operation
from ..files import FilesAccessor
from ..files.download import BotApiCredential, GraphCredential
from ..http_stream import HttpStream, StreamOptions, StreamReplyChain
from ..oauth_connection import connection_lookup_key, normalize_connection_name
from ..oauth_state import (
    get_pending_oauth_sign_ins,
    record_pending_oauth_sign_in,
    replace_pending_oauth_sign_ins,
)
from ..plan import Plan
from ..plugins.streamer import StreamerProtocol
from ..state import TurnStateContainer
from ..utils import create_graph_client

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

T = TypeVar("T", bound=ActivityBase, contravariant=True)
logger = logging.getLogger(__name__)


def _has_source_name(channel_data: Optional[ChannelData]) -> bool:
    """Whether `channel_data.source` is present, which it is when it carries a non-empty string `name`."""
    source = channel_data.source if channel_data is not None else None
    name = source.name if source is not None else None
    return isinstance(name, str) and name != ""


def _message_payload_id(value: Any) -> Optional[str]:
    """The id of `value.messagePayload`, for a typed invoke value or one that was left as a dict.

    Returns None when there is no string id.
    """
    if isinstance(value, dict):
        payload = cast(dict[str, Any], value).get("messagePayload")
        payload_id = cast(dict[str, Any], payload).get("id") if isinstance(payload, dict) else None
    else:
        payload_id = getattr(getattr(value, "message_payload", None), "id", None)
    return payload_id if isinstance(payload_id, str) else None


CONVERSATION_REF_SEND_DEPRECATION = (
    "Passing a conversation reference is deprecated and will be removed in a future release. "
    "Use `App.send()` to send to a different conversation. "
    "`App.send()` uses the service URL the app is configured with unless `service_url` is passed, "
    "unlike the context methods, which use the service URL of the conversation reference "
    "(by default, the inbound activity's)."
)


@dataclass
class SignInOptions:
    """Options for the signin method."""

    oauth_card_text: str = "Please Sign In..."
    sign_in_button_text: str = "Sign In"
    connection_name: Optional[str] = None
    override_sign_in_activity: Optional[
        Callable[
            [
                Optional[TokenExchangeResource],
                Optional[TokenPostResource],
                Optional[str],
            ],
            ActivityParams,
        ]
    ] = None


DEFAULT_SIGNIN_OPTIONS = SignInOptions()


class _ReplyChainPlacement(NamedTuple):
    chat_or_channel_id: str
    reply_chain_id: str
    in_channel: bool


class ActivityContext(Generic[T]):
    """Context object passed to activity handlers with middleware support.

    .. note::
        The single-connection OAuth surface here - :attr:`is_signed_in`,
        :attr:`user_token`, :attr:`user_graph`, :meth:`sign_in`,
        :meth:`sign_out` and :meth:`get_user_token` - predates
        multi-connection support and is deprecated.

        Register connections with
        ``app.add_oauth_flow(name)`` and use the returned ``OAuthFlow``, which
        pins every operation to the connection that owns it.
    """

    def __init__(
        self,
        activity: T,
        app_id: str,
        storage: Storage[str, Any],
        api: ApiClient,
        user_token: Optional[str],
        conversation_ref: ConversationReference,
        is_signed_in: bool,
        connection_name: str,
        app_token: Token,
        cloud: CloudEnvironment = PUBLIC,
        oauth_connection_names: Optional[Sequence[str]] = None,
        files_credential: Optional[GraphCredential] = None,
        files_bot_api_credential: Optional[BotApiCredential] = None,
    ):
        self.activity = activity
        self.app_id = app_id
        self.logger = logger
        self.conversation_ref = conversation_ref
        self.storage = storage
        self.api = api
        self.user_token = user_token
        self.connection_name = connection_name
        self.is_signed_in = is_signed_in
        self.cloud = cloud
        self.state: Optional[TurnStateContainer] = None
        self._app_token = app_token
        # Connection names of the app's registered OAuth flows, in registration
        # order. Names rather than the registry itself: the registry imports this
        # module, so holding it here would be circular.
        self._oauth_connection_names: List[str] = list(oauth_connection_names or [])
        self._stream: Optional[StreamerProtocol] = None
        self._plan: Optional[Plan] = None
        self._files: Optional[FilesAccessor] = None
        self._files_credential = files_credential
        self._files_bot_api_credential = files_bot_api_credential

        self._next_handler: Optional[Callable[[], Awaitable[None]]] = None

        # Initialize graph clients as None - they'll be created lazily
        self._user_graph: Optional["GraphServiceClient"] = None
        self._app_graph: Optional["GraphServiceClient"] = None

    @property
    def stream(self) -> StreamerProtocol:
        """The stream for the current conversation.

        The first message of the stream goes to the reply chain (thread) where ``send`` would place a response.
        In a 1:1 chat the stream goes into the reply chain when the inbound activity is inside one,
        and at top level otherwise.
        In a channel the stream goes into the reply chain of the inbound message.
        In a channel, when the service answers HTTP 404, the first message is created in the inbound conversation.
        In a group chat the stream is not placed in a reply chain.
        """
        if self._stream is None:
            placement = self._get_inbound_reply_chain_placement()
            self._stream = HttpStream(
                self.api,
                self.conversation_ref,
                StreamOptions(StreamReplyChain(placement.chat_or_channel_id, placement.reply_chain_id))
                if placement is not None
                else None,
            )
        return self._stream

    @property
    def files(self) -> FilesAccessor:
        """
        The uploaded files on the current inbound activity, i.e. the `content_type: file.download.info` subset of
        `activity.attachments`, plus images pasted inline, mapped to `IncomingFile`. See `FilesAccessor`.
        """
        if self._files is None:
            # Reuse the API client's underlying connection pool rather than building a new one per download. The raw
            # `httpx.AsyncClient` is used deliberately: the SDK wrapper injects the bot's `Authorization` header per
            # request, and a download URL carries its own `tempauth` credential that a bearer token can displace.
            self._files = FilesAccessor(
                self.activity,
                self.api.http.http,
                self._files_credential,
                self._files_bot_api_credential,
            )
        return self._files

    @experimental("ExperimentalTeamsPlan")
    def plan(self) -> Plan:
        """Create or reference the existing Plan for the incoming activity. Diagnostic: ExperimentalTeamsPlan"""
        if self._plan is None:
            self._plan = Plan(
                conversation_id=self.conversation_ref.conversation.id,
                reply_to_id=self.activity.id,
                api_client=self.api.from_service_url(self.conversation_ref.service_url),
            )
        return self._plan

    @property
    def user_graph(self) -> "GraphServiceClient":
        """
        Get a Microsoft Graph client configured with the user's token.

        .. deprecated::
            Built from :attr:`user_token`, which holds the token for whichever
            connection signed in most recently rather than the one that talks to
            Microsoft Graph.

            Read the token from the owning flow instead::
                token = await app.get_oauth_flow("graph").get_token(ctx)

        Raises:
            ValueError: If the user is not signed in or doesn't have a valid token.
            RuntimeError: If the graph client cannot be created.
            ImportError: If the graph dependencies are not installed.

        """
        if not self.is_signed_in:
            raise ValueError("User must be signed in to access Graph client")

        if not self.user_token:
            raise ValueError("No user token available for Graph client")

        if self._user_graph is None:
            try:
                user_token = JsonWebToken(self.user_token)
                self._user_graph = create_graph_client(user_token, cloud=self.cloud)
            except ImportError:
                raise
            except Exception as e:
                self.logger.error(f"Failed to create user graph client: {e}")
                raise RuntimeError(f"Failed to create user graph client: {e}") from e

        return self._user_graph

    @property
    def app_graph(self) -> "GraphServiceClient":
        """
        Get a Microsoft Graph client configured with the app's token.

        This client can be used for app-only operations that don't require user context.

        Raises:
            ValueError: If no app token is available.
            RuntimeError: If the graph client cannot be created.
            ImportError: If the graph dependencies are not installed.

        """
        if self._app_graph is None:
            try:
                self._app_graph = create_graph_client(self._app_token, cloud=self.cloud)
            except ImportError:
                raise
            except Exception as e:
                self.logger.error(f"Failed to create app graph client: {e}")
                raise RuntimeError(f"Failed to create app graph client: {e}") from e

        return self._app_graph

    @overload
    async def send(self, message: str | ActivityParams | AdaptiveCard) -> SentActivity: ...

    @overload
    @deprecated(CONVERSATION_REF_SEND_DEPRECATION)
    async def send(
        self,
        message: str | ActivityParams | AdaptiveCard,
        conversation_ref: Optional[ConversationReference] = None,
    ) -> SentActivity: ...

    async def send(
        self,
        message: str | ActivityParams | AdaptiveCard,
        conversation_ref: Optional[ConversationReference] = None,
    ) -> SentActivity:
        """Send a message in the current conversation without quoting.

        In a 1:1 chat, sends into the reply chain (thread) of the inbound activity when it is inside one.
        Otherwise it sends at top level.
        The inbound activity can be a message, a card action, an invoke, a reaction, an edit or a delete.
        In a channel, sends into the reply chain of the inbound message.
        In a channel, when the service answers HTTP 404, sends to the inbound conversation instead.
        Group chats, meetings and other inbound activities are not placed,
        and the activity is sent to the inbound conversation.
        To send with a visual quote of the inbound message, use :meth:`reply`.

        Args:
            message: The message to send, can be a string, ActivityParams, or AdaptiveCard
            conversation_ref: Conversation reference to send to a different conversation.

                .. deprecated::
                    Passing a conversation reference is deprecated and will be removed in a future release.
                    Use ``App.send()`` to send to a different conversation.
                    ``App.send()`` uses the service URL the app is configured with unless ``service_url`` is passed,
                    unlike the context methods, which use the service URL of the conversation reference
                    (by default, the inbound activity's).
        """
        if conversation_ref is not None:
            warnings.warn(CONVERSATION_REF_SEND_DEPRECATION, DeprecationWarning, stacklevel=2)
        return await self._send(message, conversation_ref)

    async def _send(
        self,
        message: str | ActivityParams | AdaptiveCard,
        conversation_ref: Optional[ConversationReference] = None,
    ) -> SentActivity:
        if isinstance(message, str):
            activity = MessageActivityInput(text=message)
        elif isinstance(message, AdaptiveCard):
            activity = MessageActivityInput().add_card(message)
        else:
            activity = message

        if self._should_outbound_be_auto_targeted(activity, conversation_ref):
            self._apply_targeted_recipient(activity)

        self._add_targeted_message_info_entity(activity)

        ref = conversation_ref or self.conversation_ref
        placement = self._get_chat_reply_chain_placement(activity, conversation_ref)
        if placement is not None:
            try:
                return await send_or_update_activity(
                    self.api,
                    activity,
                    ref.model_copy(
                        update={
                            "conversation": ref.conversation.model_copy(update={"id": placement.chat_or_channel_id})
                        }
                    ),
                    agentic_identity=self.activity.recipient.agentic_identity,
                    reply_chain_id=placement.reply_chain_id,
                )
            except HTTPStatusError as e:
                if not placement.in_channel or e.response.status_code != 404:
                    raise

        return await send_or_update_activity(
            self.api,
            activity,
            ref,
            agentic_identity=self.activity.recipient.agentic_identity,
        )

    async def reply(self, input: str | ActivityParams) -> SentActivity:
        """Send a message in the current conversation with a visual quote of the inbound message.

        In a 1:1 chat, sends into the reply chain (thread) of the inbound activity when it is inside one.
        Otherwise it sends at top level.
        The inbound activity can be a message, a card action, an invoke, a reaction, an edit or a delete.
        In a channel, sends into the reply chain of the inbound message.
        In a channel, when the service answers HTTP 404, sends to the inbound conversation instead.
        Group chats, meetings and other inbound activities are not placed,
        and the activity is sent to the inbound conversation.
        To send without quoting, use :meth:`send`.
        """
        if self.activity.id:
            return await self.quote(self.activity.id, input)
        activity = MessageActivityInput(text=input) if isinstance(input, str) else input
        return await self.send(activity)

    async def quote(self, message_id: str, input: str | ActivityParams) -> SentActivity:
        """
        Send a message to the conversation with a quoted message reference prepended to the text.
        Teams renders the quoted message as a preview bubble above the response text.

        Args:
            message_id: The ID of the message to quote
            input: The response text or activity — a quote placeholder for message_id will be prepended to its text

        Returns:
            The sent activity
        """
        activity = MessageActivityInput(text=input) if isinstance(input, str) else input
        if isinstance(activity, MessageActivityInput):
            activity.prepend_quote(message_id)
        return await self.send(activity)

    async def next(self) -> None:
        """Call the next middleware in the chain."""
        if self._next_handler:
            await self._next_handler()

    def set_next(self, handler: Callable[[], Awaitable[None]]) -> None:
        """Set the next handler in the middleware chain."""
        self._next_handler = handler

    def _incoming_targeted_sender(self) -> Optional[Account]:
        if not isinstance(self.activity, MessageActivity):
            return None

        if self.activity.recipient.is_targeted is not True:
            return None

        return self.activity.from_

    def _should_outbound_be_auto_targeted(
        self,
        activity: ActivityParams,
        conversation_ref: Optional[ConversationReference] = None,
    ) -> bool:
        if not isinstance(activity, MessageActivityInput):
            return False

        if self._incoming_targeted_sender() is None:
            return False

        if not self._is_same_conversation(conversation_ref):
            return False

        return not activity.id and activity.recipient is None

    def _get_inbound_reply_chain_placement(self) -> Optional[_ReplyChainPlacement]:
        """Find the chat or channel and reply chain (thread) a response to the inbound activity is posted to.

        In a channel a response to a message always goes to the reply chain of the inbound message.
        `channel_data.reply_chain.id` is the root of that reply chain.
        It equals the inbound message's own id for a top-level post.
        The destination is the channel, `channel_data.channel.id`.
        Other inbound activities in a channel are not placed.
        In a chat see `_is_inside_thread` for which activities are inside a thread.
        The destination is the chat, `channel_data.chat.id`.
        In a 1:1 chat, when the inbound activity is on a top-level message, the response is sent as a top-level message.
        Group chats and meetings are not placed.
        Returns None when an id is missing or blank, so the send goes to the inbound conversation.
        """
        conversation_type = self.activity.conversation.conversation_type
        if conversation_type == "groupChat":
            return None

        channel_data = self.activity.channel_data
        reply_chain_id = channel_data.reply_chain.id if channel_data and channel_data.reply_chain else None
        if reply_chain_id is None or not reply_chain_id.strip():
            return None

        if conversation_type == "channel":
            channel_id = channel_data.channel.id if channel_data and channel_data.channel else None
            if self.activity.type != "message" or channel_id is None or not channel_id.strip():
                return None
            return _ReplyChainPlacement(channel_id, reply_chain_id, True)

        chat_id = channel_data.chat.id if channel_data and channel_data.chat else None
        if chat_id is None or not chat_id.strip() or not self._is_inside_thread(reply_chain_id):
            return None
        return _ReplyChainPlacement(chat_id, reply_chain_id, False)

    def _is_inside_thread(self, reply_chain_id: str) -> bool:
        """Whether the inbound activity in a chat is inside a thread.

        That is when `channel_data.reply_chain.id` differs from the id of the message the activity acts on.
        The message it acts on is:

        - `activity.id` for a message, an edit, a delete and a reaction.
        - `reply_to_id` (the card's message) for a message sent by a card button (a message with `channel_data.source`).
        - `value.message_payload.id` for a message action, and `reply_to_id` (the message the user acted on, for
          example a card or a message with feedback buttons) for any other invoke.

        An invoke that is not tied to a message (for example a compose-box extension or a `task/fetch` from a bot
        command) is inside a thread when `channel_data.reply_chain.id` is present.
        A `reply_to_id` or `message_payload.id` that is not a plain number is never inside a thread, and neither are
        other inbound activities.
        A `source` without a non-empty string `name` and a `reply_to_id` that is null count as absent.
        """
        activity: Any = self.activity
        activity_type = activity.type

        def is_other_plain_id(message_id: Optional[str]) -> bool:
            return bool(
                message_id
                and message_id.isascii()
                and message_id.isdigit()
                and message_id != "0"
                and message_id != reply_chain_id
            )

        if activity_type == "message":
            if _has_source_name(activity.channel_data):
                return is_other_plain_id(activity.reply_to_id)
            return activity.id != reply_chain_id

        if activity_type in ("messageUpdate", "messageDelete", "messageReaction"):
            return activity.id != reply_chain_id

        if activity_type == "invoke":
            message_id = _message_payload_id(getattr(activity, "value", None))
            if message_id is None:
                message_id = activity.reply_to_id
            return True if message_id is None else is_other_plain_id(message_id)

        return False

    def _get_chat_reply_chain_placement(
        self,
        activity: ActivityParams,
        conversation_ref: Optional[ConversationReference] = None,
    ) -> Optional[_ReplyChainPlacement]:
        if (
            not isinstance(activity, MessageActivityInput)
            or activity.id
            or not self._is_same_conversation(conversation_ref)
        ):
            return None

        return self._get_inbound_reply_chain_placement()

    def _is_same_conversation(self, conversation_ref: Optional[ConversationReference] = None) -> bool:
        if conversation_ref is None:
            return True

        return conversation_ref.conversation.id == self.conversation_ref.conversation.id

    def _apply_targeted_recipient(self, activity: ActivityParams) -> None:
        sender = self._incoming_targeted_sender()
        if sender is None:
            return

        recipient = sender.model_copy()
        recipient.is_targeted = True
        activity.recipient = recipient

    def _is_targeted_outbound(self, activity: ActivityParams) -> TypeGuard[MessageActivityInput]:
        return (
            isinstance(activity, MessageActivityInput)
            and activity.recipient is not None
            and activity.recipient.is_targeted is True
        )

    def _add_targeted_message_info_entity(self, activity_params: ActivityParams) -> None:
        """Auto-populate targetedMessageInfo entity when replying to a targeted message.

        In the reactive flow, the SDK reads the incoming targeted message ID
        and attaches the entity automatically so the developer doesn't need to.
        Skips if the developer already attached a targetedMessageInfo entity.
        """
        if self._incoming_targeted_sender() is None:
            return
        if not self._is_targeted_outbound(activity_params):
            return

        activity_params.add_targeted_message_info(self.activity.id)

    async def sign_in(self, options: Optional[SignInOptions] = None) -> Optional[str]:
        """
        Initiate a sign-in flow for the user.

        .. deprecated::
            Targets the app's single ``connection_name``, which does not
            generalize past one connection. Use
            ``app.get_oauth_flow(name).sign_in(ctx, options)``, which pins the
            connection to the flow that owns it.

        Args:
            options: Optional signin options to customize the flow

        Returns:
            The token if already available, otherwise None after sending OAuth card
        """
        signin_opts = options or DEFAULT_SIGNIN_OPTIONS
        oauth_card_text = signin_opts.oauth_card_text
        sign_in_button_text = signin_opts.sign_in_button_text
        connection_name = normalize_connection_name(signin_opts.connection_name or self.connection_name)
        try:
            # Try to get existing token
            token_params = GetUserTokenParams(
                channel_id=self.activity.channel_id,
                user_id=self.activity.from_.id,
                connection_name=connection_name,
            )
            res = await self.api.users.get_token(token_params)
            return res.token
        except HTTPStatusError as e:
            # 404 is the Token Service saying "no token cached", which is the only
            # reason to fall through to a sign-in card. Anything else - a bad
            # request, an expired exchange, an outage - is a real failure and must
            # not be silently redecorated as "user needs to sign in".
            if e.response.status_code != 404:
                raise

        # Create token exchange state
        token_exchange_state = TokenExchangeState(
            connection_name=connection_name,
            conversation=self.conversation_ref,
            ms_app_id=self.app_id,
        )

        # Encode state
        state = base64.b64encode(json.dumps(token_exchange_state.model_dump()).encode()).decode()

        # Get sign-in resource
        resource_params = GetBotSignInResourceParams(state=state)
        resource = await self.api._bots.sign_in.get_resource(resource_params)  # pyright: ignore[reportPrivateUsage]

        # In group conversations (group chats and channels) the OAuth card is sent as a
        # targeted message so it is visible only to the requesting user rather than the
        # whole conversation. Channels cannot perform the silent SSO token exchange, so
        # the token exchange resource is omitted there to render the sign-in button
        # (OAuth card flow) instead of attempting an exchange that would fail.
        is_group = self.activity.conversation.is_group is True
        is_channel = self.activity.conversation.conversation_type == "channel"

        recipient = self.activity.from_.model_copy()
        if is_group:
            recipient.is_targeted = True

        token_exchange_resource = None if is_channel else resource.token_exchange_resource
        payload: ActivityParams
        if signin_opts.override_sign_in_activity is not None:
            payload = signin_opts.override_sign_in_activity(
                token_exchange_resource,
                resource.token_post_resource,
                resource.sign_in_link,
            )
            # A caller-built activity replaces the card, not the group-chat
            # targeting rule, so the requesting user is still the recipient
            # unless the override deliberately chose one.
            if is_group and hasattr(payload, "recipient") and getattr(payload, "recipient", None) is None:
                payload.recipient = recipient
        else:
            payload = MessageActivityInput(recipient=recipient).add_attachments(
                card_attachment(
                    attachment=OAuthCardAttachment(
                        content=OAuthCard(
                            text=oauth_card_text,
                            connection_name=connection_name,
                            token_exchange_resource=token_exchange_resource,
                            token_post_resource=resource.token_post_resource,
                            buttons=[
                                CardAction(
                                    type=CardActionType.SIGN_IN,
                                    title=sign_in_button_text,
                                    value=resource.sign_in_link,
                                )
                            ],
                        )
                    ),
                )
            )

        previous_pending = get_pending_oauth_sign_ins(self.state, self.activity.conversation.id, self.activity.from_.id)
        try:
            record_pending_oauth_sign_in(
                self.state,
                connection_name,
                sso_offered=token_exchange_resource is not None,
                conversation_id=self.activity.conversation.id,
                user_id=self.activity.from_.id,
            )
            if self.state is not None:
                await self.state._save()  # pyright: ignore[reportPrivateUsage]
            await self.send(payload)
        except Exception:
            # Best-effort rollback: the card never went out, so the pending hint must not
            # linger and mis-route a later callback. A failure here must not replace the
            # error the caller actually needs to see.
            try:
                replace_pending_oauth_sign_ins(
                    self.state,
                    previous_pending,
                    self.activity.conversation.id,
                    self.activity.from_.id,
                )
                if self.state is not None:
                    if self.state.user is not None:
                        self.state.user._mark_dirty()  # pyright: ignore[reportPrivateUsage]
                    await self.state._save()  # pyright: ignore[reportPrivateUsage]
            except Exception:
                self.logger.warning(
                    "Failed to roll back pending OAuth sign-in state for connection '%s'.",
                    connection_name,
                    exc_info=True,
                )
            raise

        return None

    async def sign_out(self, connection_name: Optional[str] = None) -> None:
        """
        Sign out the user by clearing their token.

        This method will remove the user's token from the storage.

        .. deprecated::
            Use ``app.get_oauth_flow(name).sign_out(ctx)``, which cannot sign
            out of the wrong connection.

        Args:
            connection_name: The connection to sign out of. Defaults to the
                app's default connection.

        Raises:
            HTTPStatusError: if the Token Service rejects the request. A failed
                sign-out leaves the token in place, so callers must be able to
                see that it did not happen.
        """
        connection_name = normalize_connection_name(connection_name or self.connection_name)
        sign_out_params = SignOutUserParams(
            channel_id=self.activity.channel_id,
            user_id=self.activity.from_.id,
            connection_name=connection_name,
        )
        await self.api.users.sign_out(sign_out_params)
        self.logger.debug(f"User {self.activity.from_.id} signed out of '{connection_name}'.")

    async def get_user_token(self, connection_name: Optional[str] = None) -> Optional[str]:
        """
        Get the user's token for a connection.

        .. deprecated::
            Use ``app.get_oauth_flow(name).get_token(ctx)``, which reads the
            token from the flow that owns the connection.

        Args:
            connection_name: The connection to read. Defaults to the app's
                default connection.

        Returns:
            The token if the user is signed in, or ``None`` if they are not
            (the Token Service returns 404 when no token is cached).

        Raises:
            HTTPStatusError: for any non-404 failure (e.g. the Token Service is
                unavailable). Such errors are surfaced rather than being masked
                as "not signed in", so a genuine outage is not mistaken for a
                logged-out user.
        """
        try:
            res = await self.api.users.get_token(
                GetUserTokenParams(
                    channel_id=self.activity.channel_id,
                    user_id=self.activity.from_.id,
                    connection_name=connection_name or self.connection_name,
                )
            )
            return res.token
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def get_connection_status(self) -> List[TokenStatus]:
        """
        Get the token status for every OAuth connection registered on the bot.

        A single Token Service call returns the status for all connections, so
        the developer never needs to enumerate connection names manually.
        Service failures propagate rather than being reported as signed out.

        The bulk call reports only connections the Token Service knows about, and
        it can lag a token that was just written. Any registered OAuth flow that
        comes back missing or ``has_token=False`` is therefore re-checked with a
        direct per-connection lookup, so a freshly signed-in flow is never
        reported as signed out. Connections that are not registered are passed
        through untouched, and a non-404 lookup failure propagates.
        """
        with trace_oauth_operation(
            APP_OAUTH_ALL_CONNECTIONS,
            APP_OAUTH_OPERATIONS.connection_status,
        ) as (_, telemetry):
            statuses = await self.api.users.get_token_status(
                GetUserTokenStatusParams(
                    channel_id=self.activity.channel_id,
                    user_id=self.activity.from_.id,
                )
            )
            if not self._oauth_connection_names:
                telemetry.result = APP_OAUTH_RESULTS.success
                return statuses

            registered = {
                key: name
                for name, key in ((name, connection_lookup_key(name)) for name in self._oauth_connection_names)
                if key is not None
            }

            corrected: List[TokenStatus] = []
            resolved: set[str] = set()
            for status in statuses:
                key = connection_lookup_key(status.connection_name)
                if key is not None:
                    resolved.add(key)
                if key is None or key not in registered or status.has_token:
                    corrected.append(status)
                    continue
                # Only reached when the bulk call said False, so a direct hit is a
                # correction and a direct miss confirms the original answer.
                if await self.get_user_token(registered[key]) is not None:
                    corrected.append(status.model_copy(update={"has_token": True}))
                else:
                    corrected.append(status)

            # Registered flows the bulk call omitted entirely.
            for key, name in registered.items():
                if key in resolved:
                    continue
                corrected.append(
                    TokenStatus(
                        channel_id=self.activity.channel_id,
                        connection_name=name,
                        has_token=await self.get_user_token(name) is not None,
                        service_provider_display_name="",
                    )
                )

            telemetry.result = APP_OAUTH_RESULTS.success
            return corrected
