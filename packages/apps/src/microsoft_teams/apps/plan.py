"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from collections.abc import Sequence
from typing import Literal

from microsoft_teams.api import (
    ApiClient,
    ConversationReference,
    MessageActivityInput,
    PlanInfoEntity,
    PlanType,
    SentActivity,
    Step,
    TypingActivityInput,
)
from microsoft_teams.common import EventEmitter
from microsoft_teams.common.experimental import experimental

from .events import ActivitySentEvent


@experimental("ExperimentalTeamsPlan")
class Plan:
    """Send prompt-bound Plan activities; the application owns ordering and concurrency.

    Preview API. Diagnostic: ExperimentalTeamsPlan
    """

    def __init__(self, api: ApiClient, conversation_ref: ConversationReference, *, reply_to_id: str) -> None:
        self._ref = conversation_ref.model_copy(deep=True)
        self._api = api.from_service_url(self._ref.service_url)
        self._reply_to_id = reply_to_id
        self.events = EventEmitter[Literal["sent"]]()

    async def start(self, steps: Sequence[Step]) -> None:
        await self._send_plan_update("start", steps)

    async def update(self, steps: Sequence[Step]) -> None:
        await self._send_plan_update("continue", steps)

    async def stop(self) -> None:
        await self._send_plan_update("stop")

    async def error(self) -> None:
        await self._send_plan_update("error")

    async def _send_plan_update(self, operation: PlanType, steps: Sequence[Step] | None = None) -> None:
        entity = PlanInfoEntity(plan_type=operation, steps=list(steps) if steps is not None else None)
        activity = TypingActivityInput(entities=[entity]).model_copy(deep=True)
        await self._send_activity(activity)

    async def complete_plan(self, message: str | MessageActivityInput) -> SentActivity:
        """Complete the Plan with a new message.

        Raises:
            ValueError: If the message contains a non-complete Plan operation.
        """
        activity = MessageActivityInput(text=message) if isinstance(message, str) else message.model_copy(deep=True)
        plan_entities = [entity for entity in activity.entities or [] if isinstance(entity, PlanInfoEntity)]
        if any(entity.plan_type != "complete" for entity in plan_entities):
            raise ValueError("complete_plan() cannot send non-complete Plan operations.")
        if not plan_entities:
            activity.add_entity(PlanInfoEntity(plan_type="complete"))
        return await self._send_activity(activity)

    async def _send_activity(self, activity: MessageActivityInput | TypingActivityInput) -> SentActivity:
        activity.reply_to_id = self._reply_to_id
        activity.from_ = self._ref.bot.model_copy(deep=True)
        activity.conversation = self._ref.conversation.model_copy(deep=True)
        result = await self._api.conversations.create_activity(self._ref.conversation.id, activity)
        self.events.emit("sent", ActivitySentEvent(activity=result, conversation_ref=self._ref.model_copy(deep=True)))
        return result
