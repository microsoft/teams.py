"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from collections.abc import Sequence

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


class Plan:
    """Send prompt-bound Plan activities; the application owns ordering and concurrency."""

    def __init__(self, api: ApiClient, conversation_ref: ConversationReference, *, reply_to_id: str) -> None:
        self._ref = conversation_ref.model_copy(deep=True)
        self._api = api.from_service_url(self._ref.service_url)
        self._reply_to_id = reply_to_id

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
        activity = TypingActivityInput(
            reply_to_id=self._reply_to_id,
            from_=self._ref.bot,
            conversation=self._ref.conversation,
            entities=[entity],
        ).model_copy(deep=True)
        await self._api.conversations.create_activity(self._ref.conversation.id, activity)

    async def complete_plan(self, message: str | MessageActivityInput) -> SentActivity:
        activity = MessageActivityInput(text=message) if isinstance(message, str) else message.model_copy(deep=True)
        if not any(isinstance(entity, PlanInfoEntity) for entity in activity.entities or []):
            activity.add_entity(PlanInfoEntity(plan_type="complete"))
        activity.reply_to_id = self._reply_to_id
        activity.from_ = self._ref.bot.model_copy(deep=True)
        activity.conversation = self._ref.conversation.model_copy(deep=True)
        return await self._api.conversations.create_activity(self._ref.conversation.id, activity)
