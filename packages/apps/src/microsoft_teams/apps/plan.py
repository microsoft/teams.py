"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from collections.abc import Sequence

from microsoft_teams.api import (
    Account,
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
    """Send prompt-bound Plan activities; the application owns ordering and concurrency.

    Targeted prompts inherit their audience from the saved conversation reference.
    An optional recipient, including its is_targeted flag, supplies the default for
    every Plan activity. A completion message's own recipient takes precedence.
    """

    def __init__(
        self,
        api: ApiClient,
        conversation_ref: ConversationReference,
        *,
        reply_to_id: str,
        recipient: Account | None = None,
    ) -> None:
        self._ref = conversation_ref.model_copy(deep=True)
        self._api = api.from_service_url(self._ref.service_url)
        self._reply_to_id = reply_to_id
        self._recipient = recipient.model_copy(deep=True) if recipient is not None else None

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
        """Complete the Plan, preserving inherited or explicit targeting.

        Raises:
            ValueError: If the message contains a non-complete Plan operation,
                or the targeted conversation reference is missing its sender.
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
        if activity.recipient is None and self._recipient is not None:
            activity.recipient = self._recipient.model_copy(deep=True)

        incoming_targeted = self._ref.bot.is_targeted is True
        if incoming_targeted and activity.recipient is None:
            if self._ref.user is None:
                raise ValueError("A targeted conversation reference must include its sender in user.")
            activity.recipient = self._ref.user.model_copy(deep=True)
            activity.recipient.is_targeted = True

        is_targeted = activity.recipient is not None and activity.recipient.is_targeted is True
        if incoming_targeted and is_targeted and isinstance(activity, MessageActivityInput):
            prompt_id = self._ref.activity_id or activity.reply_to_id
            if prompt_id:
                activity.add_targeted_message_info(prompt_id)
        if is_targeted:
            return await self._api.conversations.create_targeted_activity(self._ref.conversation.id, activity)
        return await self._api.conversations.create_activity(self._ref.conversation.id, activity)
