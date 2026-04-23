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
from a2a_client import is_allowed_peer
from cards import ask_card, reply_card
from microsoft_teams.apps import App
from state import BotState

# A2A server-side dispatch. Reads the incoming `DataPart`, branches on
# `data.kind` (`ask` vs `reply`), updates `BotState`, and builds the Teams
# card locally from the payload.

logger = logging.getLogger(__name__)


def first_data_part(message: Optional[Message]) -> dict[str, Any]:
    # A2A messages can carry multiple parts; this sample only uses one
    # DataPart per message, so pull that out.
    if message is None:
        return {}
    for part in message.parts:
        if isinstance(part.root, DataPart):
            return part.root.data
    return {}


class AskReplyExecutor(AgentExecutor):
    def __init__(self, teams_app: App, state: BotState, allowed_peer_urls: list[str]) -> None:
        self._teams_app = teams_app
        self._state = state
        self._allowed_peer_urls = allowed_peer_urls

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

        # A2A tasks need a terminal status event to close out. Our "real"
        # response (if any) flows later as a separate inbound A2A message
        # from the peer, so we just ack this one and finish.
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
        # Peer is asking us a question. Stash routing by qid and push the
        # ask card to our operator.
        qid = data.get("qid", "")
        sender = data.get("sender", "")
        question = data.get("question", "")
        reply_url = data.get("reply_url", "")
        logger.info("[%s] received ask qid=%s from %s", self._state.name, qid, sender)
        conv_id = self._state.operator_conv_id
        if not conv_id or not qid or not question:
            logger.warning("[%s] no operator conversation or missing fields; ask not pushed", self._state.name)
            return
        # Validate reply_url before we stash it or push a card tied to it.
        if not is_allowed_peer(reply_url, self._allowed_peer_urls):
            logger.warning("[%s] rejecting ask qid=%s: reply_url %r not in allowlist", self._state.name, qid, reply_url)
            return
        self._state.inbound_asks[qid] = {
            "reply_url": reply_url,
            "sender": sender,
            "question": question,
        }
        await self._teams_app.send(conv_id, ask_card(sender=sender, question=question, qid=qid))

    async def _on_reply(self, data: dict[str, Any]) -> None:
        # Peer is answering a question we originally sent. Push the reply
        # card to the user who asked.
        qid = data.get("qid", "")
        pending = self._state.awaiting_reply.pop(qid, None)
        logger.info("[%s] received reply qid=%s", self._state.name, qid)
        if not pending:
            logger.warning("[%s] no awaiting conversation for qid=%s", self._state.name, qid)
            return
        answer = data.get("answer", "")
        responder = data.get("responder", "")
        card = reply_card(responder=responder, question=pending["question"], answer=answer, qid=qid)
        await self._teams_app.send(pending["conv_id"], card)
