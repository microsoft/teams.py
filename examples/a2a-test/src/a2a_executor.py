"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid
from typing import Optional

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
from messages import A2AMessage, A2AMessageAdapter, AskMessage, ReplyMessage
from microsoft_teams.apps import App
from pydantic import ValidationError
from state import BotState

# A2A server-side dispatch. Reads the incoming `DataPart`, branches on
# `data.kind` (`ask` vs `reply`), updates `BotState`, and builds the Teams
# card locally from the payload.

logger = logging.getLogger(__name__)


def parse_a2a_message(message: Optional[Message]) -> Optional[A2AMessage]:
    # A2A messages can carry multiple parts; this sample only uses one
    # DataPart per message. Validate it against the discriminated union so
    # the executor never handles a raw dict.
    if message is None:
        return None
    for part in message.parts:
        if isinstance(part.root, DataPart):
            try:
                return A2AMessageAdapter.validate_python(part.root.data)
            except ValidationError as e:
                logger.warning("invalid a2a message: %s", e)
                return None
    return None


class AskReplyExecutor(AgentExecutor):
    def __init__(self, teams_app: App, state: BotState, allowed_peer_urls: list[str]) -> None:
        self._teams_app = teams_app
        self._state = state
        self._allowed_peer_urls = allowed_peer_urls

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())
        message = parse_a2a_message(context.message)

        if isinstance(message, AskMessage):
            await self._on_ask(message)
        elif isinstance(message, ReplyMessage):
            await self._on_reply(message)

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

    async def _on_ask(self, msg: AskMessage) -> None:
        # Peer is asking us a question. Stash routing by qid and push the
        # ask card to our operator.
        logger.info("[%s] received ask qid=%s from %s", self._state.name, msg.qid, msg.sender)
        conv_id = self._state.operator_conv_id
        if not conv_id:
            logger.warning("[%s] no operator conversation; ask not pushed", self._state.name)
            return
        # Validate reply_url before we stash it or push a card tied to it.
        if not is_allowed_peer(msg.reply_url, self._allowed_peer_urls):
            logger.warning(
                "[%s] rejecting ask qid=%s: reply_url %r not in allowlist", self._state.name, msg.qid, msg.reply_url
            )
            return
        self._state.inbound_asks[msg.qid] = {
            "reply_url": msg.reply_url,
            "sender": msg.sender,
            "question": msg.question,
        }
        await self._teams_app.send(conv_id, ask_card(sender=msg.sender, question=msg.question, qid=msg.qid))

    async def _on_reply(self, msg: ReplyMessage) -> None:
        # Peer is answering a question we originally sent. Push the reply
        # card to the user who asked.
        pending = self._state.awaiting_reply.pop(msg.qid, None)
        logger.info("[%s] received reply qid=%s", self._state.name, msg.qid)
        if not pending:
            logger.warning("[%s] no awaiting conversation for qid=%s", self._state.name, msg.qid)
            return
        card = reply_card(responder=msg.responder, question=pending["question"], answer=msg.answer, qid=msg.qid)
        await self._teams_app.send(pending["conv_id"], card)
