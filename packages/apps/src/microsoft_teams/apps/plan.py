"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from collections.abc import Sequence
from typing import Literal, TypedDict, Unpack

from microsoft_teams.api import (
    ApiClient,
    ConversationAccount,
    CustomBaseModel,
    MessageActivityInput,
    PlanInfoEntity,
    PlanType,
    SentActivity,
    Step,
    TypingActivityInput,
)
from microsoft_teams.common import EventEmitter
from microsoft_teams.common.experimental import experimental

logger = logging.getLogger(__name__)


class PlanOptions(TypedDict):
    """
    Metadata for a prompt-bound Plan continuation.

    A Plan belongs to a single conversation and prompt. ``reply_to_id`` should be the activity ID of the
    prompt that launched the Plan, not a later event ID. For an incoming activity, this is
    typically the current activity's ID, which matches the inbound
    ``conversation_ref.activity_id`` for the prompt being continued.

    ``conversation_id`` identifies the Teams conversation and is used as the outbound
    conversation target for each Plan send. The runtime client is scoped to the matching
    service URL before sends, while the serialized Plan itself remains a lightweight record
    of the conversation and prompt binding.

    ``api_client`` is runtime-only and intentionally excluded from model serialization.
    """

    conversation_id: str
    reply_to_id: str
    api_client: ApiClient


@experimental("ExperimentalTeamsPlan")
class Plan(CustomBaseModel):
    """
    Send prompt-bound Plan activities; the application owns ordering and concurrency.

    A Plan is bound to a single conversation and a single originating prompt
    (``reply_to_id``), and it does not hold a mutable conversation reference or a hidden
    live session object. The runtime client is injected separately and is scoped to the
    conversation's service URL before use.

    Preview API. Diagnostic: ExperimentalTeamsPlan
    """

    conversation_id: str
    reply_to_id: str

    def __init__(self, **options: Unpack[PlanOptions]) -> None:
        data = {"conversation_id": options["conversation_id"], "reply_to_id": options["reply_to_id"]}
        super().__init__(**data)
        self._api = options["api_client"]
        self._events = EventEmitter[Literal["sent"]]()

    @property
    def events(self) -> EventEmitter[Literal["sent"]]:
        """Emit lifecycle notifications for successfully sent Plan activities.

        The emitter exposes a single event named ``"sent"``. The payload is the
        ``SentActivity`` returned from the API after the activity is created. The event
        fires once the underlying create request succeeds and before the method returns.
        """
        return self._events

    async def start(self, steps: Sequence[Step]) -> None:
        """Start a new Plan for the bound prompt.

        Args:
            steps: Ordered step list to include in the start payload.

        Returns:
            None. The send result is exposed via the ``sent`` event.

        Raises:
            Any API/network exceptions raised by the underlying conversation client.
        """
        await self._send_plan_update("start", steps)

    async def update(self, steps: Sequence[Step]) -> None:
        """Send a continuing Plan update for the current prompt.

        Args:
            steps: New or updated plan steps describing the current state.

        Returns:
            None. This method emits the ``sent`` event on a successful response.

        Raises:
            Any API/network exceptions raised by the underlying conversation client.
        """
        await self._send_plan_update("continue", steps)

    async def stop(self) -> None:
        """Stop the active Plan for the bound prompt.

        Returns:
            None. This sends a ``planInfo`` entity with ``planType`` of ``"stop"`` and
            emits ``sent`` after success.

        Raises:
            Any API/network exceptions raised by the underlying conversation client.
        """
        await self._send_plan_update("stop")

    async def error(self) -> None:
        """Signal an error state for the active Plan.

        Returns:
            None. This sends a ``planInfo`` entity with ``planType`` of ``"error"`` and
            emits ``sent`` after success.

        Raises:
            Any API/network exceptions raised by the underlying conversation client.
        """
        await self._send_plan_update("error")

    async def _send_plan_update(self, operation: PlanType, steps: Sequence[Step] | None = None) -> None:
        logger.debug(
            "Sending Plan operation '%s' for conversation_id=%s reply_to_id=%s step_count=%s",
            operation,
            self.conversation_id,
            self.reply_to_id,
            len(steps) if steps is not None else 0,
        )
        entity = PlanInfoEntity(plan_type=operation, steps=list(steps) if steps is not None else None)
        activity = TypingActivityInput(entities=[entity]).model_copy(deep=True)
        await self._send_activity(activity)

    async def complete(self, message: str | MessageActivityInput) -> SentActivity:
        """Complete the Plan and send the final response.

        Args:
            message: Final response text or a full ``MessageActivityInput`` payload. If the
                payload already contains a ``planInfo`` entity, it must be a ``complete``
                operation; other plan operations are rejected.

        Returns:
            The ``SentActivity`` returned by the underlying conversation API call.

        Raises:
            ValueError: If the supplied message includes any ``PlanInfoEntity`` whose
                ``plan_type`` is not ``"complete"``.
            Any API/network exceptions raised by the underlying conversation client.
        """
        logger.debug(
            "Completing Plan for conversation_id=%s reply_to_id=%s message_type=%s",
            self.conversation_id,
            self.reply_to_id,
            "str" if isinstance(message, str) else type(message).__name__,
        )
        activity = MessageActivityInput(text=message) if isinstance(message, str) else message.model_copy(deep=True)
        plan_entities = [entity for entity in activity.entities or [] if isinstance(entity, PlanInfoEntity)]
        if any(entity.plan_type != "complete" for entity in plan_entities):
            raise ValueError("complete() cannot send non-complete Plan operations.")
        if not plan_entities:
            activity.add_entity(PlanInfoEntity(plan_type="complete"))
        return await self._send_activity(activity)

    async def _send_activity(self, activity: MessageActivityInput | TypingActivityInput) -> SentActivity:
        activity.reply_to_id = self.reply_to_id
        activity.conversation = ConversationAccount(id=self.conversation_id)
        result = await self._api.conversations.create_activity(self.conversation_id, activity)
        self.events.emit("sent", result)
        return result
