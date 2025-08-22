"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import base64
import json
from dataclasses import dataclass
from logging import Logger
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar, cast

from microsoft.teams.api import (
    ActivityBase,
    ActivityParams,
    ApiClient,
    CardAction,
    CardActionType,
    ConversationReference,
    CreateConversationParams,
    GetBotSignInResourceParams,
    GetUserTokenParams,
    MessageActivityInput,
    SentActivity,
    SignOutUserParams,
    TokenExchangeResource,
    TokenExchangeState,
    TokenPostResource,
    TokenProtocol,
)
from microsoft.teams.api.models.attachment.card_attachment import OAuthCardAttachment, card_attachment
from microsoft.teams.api.models.oauth import OAuthCard
from microsoft.teams.cards import AdaptiveCard
from microsoft.teams.common import Storage

from ..plugins import Sender

T = TypeVar("T", bound=ActivityBase, contravariant=True)

SendCallable = Callable[[str | ActivityParams | AdaptiveCard], Awaitable[SentActivity]]


@dataclass
class SignInOptions:
    """Options for the signin method."""

    oauth_card_text: str = "Please Sign In..."
    sign_in_button_text: str = "Sign In"
    override_sign_in_activity: Optional[
        Callable[[Optional[TokenExchangeResource], Optional[TokenPostResource], Optional[str]], ActivityParams]
    ] = None


DEFAULT_SIGNIN_OPTIONS = SignInOptions()


class ActivityContext(Generic[T]):
    """Context object passed to activity handlers with middleware support."""

    def __init__(
        self,
        activity: T,
        app_id: str,
        logger: Logger,
        storage: Storage[str, Any],
        api: ApiClient,
        user_token: Optional[TokenProtocol],
        conversation_ref: ConversationReference,
        is_signed_in: bool,
        connection_name: str,
        sender: Sender,
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
        self._plugin = sender

        self._next_handler: Optional[Callable[[], Awaitable[None]]] = None

    async def send(
        self, message: str | ActivityParams | AdaptiveCard, conversation_ref: Optional[ConversationReference] = None
    ) -> SentActivity:
        """
        Send a message to the conversation.

        Args:
            message: The message to send, can be a string, ActivityParams, or AdaptiveCard
            conversation_id: Optional conversation ID to override the current conversation reference
        """
        if isinstance(message, str):
            activity = MessageActivityInput(text=message)
        elif isinstance(message, AdaptiveCard):
            activity = MessageActivityInput().add_card(message)
        else:
            activity = message

        ref = conversation_ref or self.conversation_ref
        res = await self._plugin.send(activity, ref)
        return res

    async def reply(self, input: str | ActivityParams) -> SentActivity:
        """Send a reply to the activity."""
        activity = MessageActivityInput(text=input) if isinstance(input, str) else input
        if isinstance(activity, MessageActivityInput):
            block_quote = self._build_block_quote_for_activity()
            if block_quote:
                activity.text = f"{block_quote}\n\n{activity.text}" if activity.text else block_quote
        activity.reply_to_id = self.activity.id
        return await self.send(activity)

    async def next(self) -> None:
        """Call the next middleware in the chain."""
        if self._next_handler:
            await self._next_handler()

    def set_next(self, handler: Callable[[], Awaitable[None]]) -> None:
        """Set the next handler in the middleware chain."""
        self._next_handler = handler

    def _build_block_quote_for_activity(self) -> Optional[str]:
        if self.activity.type == "message" and hasattr(self.activity, "text"):
            activity = cast(MessageActivityInput, self.activity)
            max_length = 120
            text = activity.text or ""
            truncated_text = f"{text[:max_length]}..." if len(text) > max_length else text

            activity_id = activity.id
            from_id = activity.from_.id if activity.from_ else ""
            from_name = activity.from_.name if activity.from_ else ""

            return (
                f'<blockquote itemscope="" itemtype="http://schema.skype.com/Reply" itemid="{activity_id}">'
                f'<strong itemprop="mri" itemid="{from_id}">{from_name}</strong>'
                f'<span itemprop="time" itemid="{activity_id}"></span>'
                f'<p itemprop="preview">{truncated_text}</p>'
                f"</blockquote>"
            )
        else:
            self.logger.debug("Skipping building blockquote for activity type: %s", type(self.activity).__name__)
        return None

    async def sign_in(self, options: Optional[SignInOptions] = None) -> Optional[str]:
        """
        Initiate a sign-in flow for the user.

        Args:
            options: Optional signin options to customize the flow

        Returns:
            The token if already available, otherwise None after sending OAuth card
        """
        signin_opts = options or DEFAULT_SIGNIN_OPTIONS
        oauth_card_text = signin_opts.oauth_card_text
        sign_in_button_text = signin_opts.sign_in_button_text

        try:
            # Try to get existing token
            token_params = GetUserTokenParams(
                channel_id=self.activity.channel_id,
                user_id=self.activity.from_.id,
                connection_name=self.connection_name,
            )
            res = await self.api.users.token.get(token_params)
            return res.token
        except Exception:
            # Token not available, continue with OAuth flow
            pass

        # Create token exchange state
        token_exchange_state = TokenExchangeState(
            connection_name=self.connection_name,
            conversation=self.conversation_ref,
            relates_to=self.activity.relates_to,
            ms_app_id=self.app_id,
        )

        # Check if this is a group conversation
        # if it's a group conversation, then we create a 1:1 conversation with the user
        # and send the OAuth card there since group oauth currently isn't released.
        conversation_id = self.conversation_ref.conversation.id
        if self.activity.conversation.is_group:
            one_on_one_conversation = await self.api.conversations.create(
                CreateConversationParams(
                    tenant_id=self.activity.conversation.tenant_id,
                    is_group=False,
                    bot=self.activity.recipient,
                    members=[self.activity.from_],
                )
            )
            conversation_id = one_on_one_conversation.id
            await self.send(MessageActivityInput(text=oauth_card_text))

        # Encode state
        state = base64.b64encode(json.dumps(token_exchange_state.model_dump()).encode()).decode()

        # Get sign-in resource
        resource_params = GetBotSignInResourceParams(state=state)
        resource = await self.api.bots.sign_in.get_resource(resource_params)

        payload = MessageActivityInput(recipient=self.activity.from_, input_hint="acceptingInput").add_attachments(
            card_attachment(
                attachment=OAuthCardAttachment(
                    content=OAuthCard(
                        text=oauth_card_text,
                        connection_name=self.connection_name,
                        token_exchange_resource=resource.token_exchange_resource,
                        token_post_resource=resource.token_post_resource,
                        buttons=[
                            CardAction(
                                type=CardActionType.SIGN_IN, title=sign_in_button_text, value=resource.sign_in_link
                            )
                        ],
                    )
                ),
            )
        )

        self.conversation_ref.conversation.id = conversation_id
        await self.send(payload, self.conversation_ref)

        return None

    async def sign_out(self) -> None:
        """
        Sign out the user by clearing their token.

        This method will remove the user's token from the storage.
        """
        try:
            sign_out_params = SignOutUserParams(
                channel_id=self.activity.channel_id,
                user_id=self.activity.from_.id,
                connection_name=self.connection_name,
            )
            await self.api.users.token.sign_out(sign_out_params)
            self.logger.debug(f"User {self.activity.from_.id} signed out successfully.")
        except Exception as e:
            self.logger.error(f"Failed to sign out user: {e}")
