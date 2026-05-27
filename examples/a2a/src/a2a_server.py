"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.apps.jsonrpc.starlette_app import A2AStarletteApplication
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers.default_request_handler import DefaultRequestHandler
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    DataPart,
    Message,
    Part,
    Role,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)
from agent import BotAgent
from microsoft_teams.api import Account, CreateConversationParams
from microsoft_teams.api.clients.conversation.client import ConversationClient
from microsoft_teams.apps import App
from pydantic import ValidationError
from types_ import Config, HandoffMessage

logger = logging.getLogger(__name__)


def _extract_handoff(context: RequestContext) -> HandoffMessage | None:
    """Pull a HandoffMessage out of the first DataPart in the inbound A2A message."""
    msg: Message | None = context.message
    if msg is None:
        return None
    for part in msg.parts:
        if isinstance(part.root, DataPart):
            try:
                return HandoffMessage.model_validate(part.root.data)
            except (ValidationError, Exception) as exc:
                logger.warning("invalid handoff payload: %s", exc)
                return None
    return None


class HandoffAgentExecutor(AgentExecutor):
    """Inbound A2A executor.

    For every inbound A2A message:
    1. Extract the HandoffMessage from the DataPart.
    2. Create a fresh 1:1 conversation with the user via their ``serviceUrl``.
    3. Ask the agent to seed that conversation's history with handoff context + greeting.
    4. Send the greeting proactively.
    5. Publish a short ack so the sending bot's ``sendMessage`` resolves.
    """

    def __init__(self, app: App, agent: BotAgent, config: Config) -> None:
        self._app = app
        self._agent = agent
        self._config = config

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or str(uuid.uuid4())
        context_id = context.context_id or str(uuid.uuid4())

        handoff = _extract_handoff(context)
        if not handoff:
            await self._ack(event_queue, task_id, context_id, "Unsupported or incomplete handoff message.")
            return

        logger.info(
            "[%s/A2A] received handoff: from=%s user=%s aadId=%s tenant=%s",
            self._config.name,
            handoff.from_,
            handoff.user_name,
            handoff.aad_object_id,
            handoff.tenant_id,
        )

        try:
            new_conv_id = await self._open_dm_with_user(handoff)
            greeting = await self._agent.greet_with_handoff(new_conv_id, handoff)
            await self._app.send(new_conv_id, greeting)
            logger.info("[%s/A2A] proactive greeting sent (conv=%s)", self._config.name, new_conv_id)
            await self._ack(
                event_queue, task_id, context_id, f"Handoff received and {handoff.user_name} contacted directly."
            )
        except Exception as exc:
            logger.error("[%s/A2A] handoff failed: %s", self._config.name, exc)
            await self._ack(event_queue, task_id, context_id, f"Handoff failed: {exc}")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        # Handoffs are single-shot; nothing to cancel.
        pass

    async def _open_dm_with_user(self, handoff: HandoffMessage) -> str:
        """Create a 1:1 conversation with the user via THEIR serviceUrl."""
        conv_client = ConversationClient(
            service_url=handoff.service_url,
            options=self._app.api.http,
        )
        result = await conv_client.create(
            CreateConversationParams(
                members=[Account(id=handoff.aad_object_id, name=handoff.user_name, type="bot")],
                tenant_id=handoff.tenant_id,
            )
        )
        if not result.id:
            raise RuntimeError("CreateConversation returned no conversation id.")
        return result.id

    @staticmethod
    async def _ack(event_queue: EventQueue, task_id: str, context_id: str, text: str) -> None:
        ack_msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.agent,
            parts=[Part(root=DataPart(data={"text": text}))],
        )
        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.completed, message=ack_msg),
                final=True,
            )
        )


def build_agent_card(config: Config) -> AgentCard:
    """Build the AgentCard that describes this bot to peer agents."""
    a2a_url = config.self_url.rstrip("/") + "/a2a"
    return AgentCard(
        name=config.name,
        description=config.description,
        url=a2a_url,
        version="1.0.0",
        protocol_version="0.3.0",
        default_input_modes=["application/json"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="handoff",
                name="Handoff",
                description=f"Accepts handoffs of users from peer bots. Specialty: {config.description}",
                tags=["a2a", "teams", "handoff"],
            )
        ],
    )


def make_a2a_app(
    *,
    teams_app: App,
    agent: BotAgent,
    config: Config,
    agent_card: AgentCard,
) -> A2AStarletteApplication:
    """Build the A2A Starlette sub-application to mount at ``/a2a``."""
    handler = DefaultRequestHandler(
        agent_executor=HandoffAgentExecutor(teams_app, agent, config),
        task_store=InMemoryTaskStore(),
    )
    return A2AStarletteApplication(agent_card=agent_card, http_handler=handler)
