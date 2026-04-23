"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid
from typing import Any, Optional

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.types import (
    DataPart,
    Message,
    Part,
    Role,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from microsoft_teams.apps import App
from microsoft_teams.cards import AdaptiveCard
from state import BotState

# A2A server-side dispatch. Reads the incoming `DataPart`, branches on
# `data.kind` (`ask` vs `reply`), updates `BotState`, and pushes the right card
# into Teams via `app.send(conv_id, card)`.

logger = logging.getLogger(__name__)


def first_data_part(message: Optional[Message]) -> dict[str, Any]:
    if message is None:
        return {}
    for part in message.parts:
        if isinstance(part.root, DataPart):
            return part.root.data
    return {}


class AskReplyExecutor(AgentExecutor):
    def __init__(self, teams_app: App, state: BotState) -> None:
        self._teams_app = teams_app
        self._state = state

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        data = first_data_part(context.message)
        kind = data.get("kind")

        if kind == "ask":
            await self._on_ask(data)
        elif kind == "reply":
            await self._on_reply(data)
        else:
            logger.warning("unknown a2a kind: %r", kind)

        ack = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[Part(root=DataPart(data={"kind": "ack"}))],
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.completed, message=ack),
                final=True,
            )
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id or str(uuid.uuid4()),
                context_id=context.context_id or str(uuid.uuid4()),
                status=TaskStatus(state=TaskState.canceled),
                final=True,
            )
        )

    async def _on_ask(self, data: dict[str, Any]) -> None:
        qid = data.get("qid", "")
        logger.info("[%s] received ask qid=%s from %s", self._state.name, qid, data.get("sender"))
        conv_id = self._state.operator_conv_id
        card = data.get("card")
        if not conv_id or not card:
            logger.warning("[%s] no operator conversation; ask not pushed", self._state.name)
            return
        await self._teams_app.send(conv_id, AdaptiveCard.model_validate(card))

    async def _on_reply(self, data: dict[str, Any]) -> None:
        qid = data.get("qid", "")
        pending = self._state.awaiting_reply.pop(qid, None)
        logger.info("[%s] received reply qid=%s", self._state.name, qid)
        if not pending:
            logger.warning("[%s] no awaiting conversation for qid=%s", self._state.name, qid)
            return
        card = data.get("card")
        if card:
            await self._teams_app.send(pending["conv_id"], AdaptiveCard.model_validate(card))
