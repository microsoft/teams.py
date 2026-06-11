"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass

from microsoft_teams.api import (
    Account,
    ActivityParams,
    ConversationAccount,
    ConversationReference,
    MessageActivityInput,
    SentActivity,
)
from microsoft_teams.cards import AdaptiveCard
from microsoft_teams.common import Client, ClientOptions

from .activity_sender import ActivitySender
from .token_manager import TokenManager
from .utils.thread import to_threaded_conversation_id


@dataclass(frozen=True)
class AgentUserIdentity:
    """Identifies an Agent ID user-shaped identity and its backing agent app."""

    id: str
    agent_identity_app_id: str
    tenant_id: str


class AgentUser:
    """A sendable Agent ID user identity."""

    def __init__(
        self,
        identity: AgentUserIdentity,
        *,
        service_url: str,
        http_client: Client,
        token_manager: TokenManager,
    ):
        self.identity = identity
        self._service_url = service_url.rstrip("/")
        self._activity_sender = ActivitySender(http_client.clone(ClientOptions(token=self._get_bot_token)))
        self._token_manager = token_manager

    @property
    def id(self) -> str:
        return self.identity.id

    @property
    def agent_identity_app_id(self) -> str:
        return self.identity.agent_identity_app_id

    @property
    def tenant_id(self) -> str:
        return self.identity.tenant_id

    async def send(
        self,
        conversation: str | ConversationReference,
        activity: str | ActivityParams | AdaptiveCard,
    ) -> SentActivity:
        """Send an activity as this agent user."""
        if isinstance(conversation, str):
            ref = ConversationReference(
                channel_id="msteams",
                service_url=self._service_url,
                bot=Account(id=self._channel_account_id),
                conversation=ConversationAccount(id=conversation),
            )
        else:
            ref = conversation.model_copy(deep=True)

        ref.bot = Account(id=self._channel_account_id)
        return await self._activity_sender.send(ref, self._coerce_activity(activity))

    @property
    def _channel_account_id(self) -> str:
        return self.id if self.id.startswith("8:") else f"8:orgid:{self.id}"

    async def _get_bot_token(self):
        return await self._token_manager.get_agent_bot_token(
            self.identity.tenant_id,
            self.identity.agent_identity_app_id,
            agent_user_id=self.identity.id,
        )

    async def reply(
        self,
        conversation_id: str,
        message_id: str | ActivityParams | AdaptiveCard = "",
        activity: str | ActivityParams | AdaptiveCard | None = None,
    ) -> SentActivity:
        """Send as this agent user, optionally to a threaded reply target."""
        if activity is not None:
            if not isinstance(message_id, str):
                raise TypeError("message_id must be a string when activity is provided")
            return await self.send(to_threaded_conversation_id(conversation_id, message_id), activity)

        return await self.send(conversation_id, message_id)

    def _coerce_activity(self, activity: str | ActivityParams | AdaptiveCard) -> ActivityParams:
        if isinstance(activity, str):
            return MessageActivityInput(text=activity)
        if isinstance(activity, AdaptiveCard):
            return MessageActivityInput().add_card(activity)
        return activity


__all__ = ["AgentUser", "AgentUserIdentity"]
