"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid
from contextvars import ContextVar
from os import getenv
from typing import Annotated

import httpx
from a2a.client import A2ACardResolver
from a2a.types import AgentCard
from a2a_client import send_a2a
from agent_framework import Agent, AgentSession, Message, tool
from agent_framework._sessions import InMemoryHistoryProvider
from agent_framework.openai import OpenAIChatClient
from dotenv import find_dotenv, load_dotenv
from messages import AskMessage
from pydantic import Field
from state import BotState

# LLM-driven routing for the Teams bot. The agent has one tool,
# `send_to_peer`, whose system prompt advertises peers using the
# `description` field from each peer's A2A AgentCard (fetched lazily).

load_dotenv(find_dotenv(usecwd=True))
logger = logging.getLogger(__name__)


# Per-turn context the tool reads to know which Teams conversation it's
# serving. Set in handle_message before `agent.run(...)`.
current_user_conv_id: ContextVar[str] = ContextVar("current_user_conv_id")


def _require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"Required environment variable {name!r} is not set.")
    return value


class BotAgent:
    def __init__(
        self,
        self_name: str,
        self_a2a_url: str,
        peers: dict[str, str],  # peer_name -> A2A URL
        state: BotState,
    ) -> None:
        self._self_name = self_name
        self._self_a2a_url = self_a2a_url
        self._peers = peers
        self._state = state
        self._peer_cards: dict[str, AgentCard] = {}
        self._sessions: dict[str, AgentSession] = {}
        self._client = OpenAIChatClient(
            model=_require_env("AZURE_OPENAI_MODEL"),
            azure_endpoint=_require_env("AZURE_OPENAI_ENDPOINT"),
            api_key=_require_env("AZURE_OPENAI_API_KEY"),
        )

    async def _refresh_peer_cards(self) -> None:
        # Lazy fetch — each turn, fill in any peers we couldn't reach yet.
        # Once cached, never refetched (peers don't change descriptions
        # at runtime in this sample).
        missing = [name for name in self._peers if name not in self._peer_cards]
        if not missing:
            return
        async with httpx.AsyncClient(timeout=10.0) as http:
            for name in missing:
                try:
                    card = await A2ACardResolver(http, self._peers[name]).get_agent_card()
                    self._peer_cards[name] = card
                    logger.info("[%s] resolved peer card: %s", self._self_name, name)
                except Exception as e:
                    logger.warning("[%s] could not resolve peer card %s: %s", self._self_name, name, e)

    def _format_peers(self) -> str:
        lines: list[str] = []
        for name in self._peers:
            card = self._peer_cards.get(name)
            if card is None:
                lines.append(f"- {name}: (peer card not yet reachable; ask cautiously)")
                continue
            skills = "; ".join(s.description or s.name for s in (card.skills or []))
            entry = f"- {name}: {card.description}"
            if skills:
                entry += f" Skills: {skills}."
            lines.append(entry)
        return "\n".join(lines)

    def _build_agent(self) -> Agent:
        peer_names = ", ".join(self._peers)

        @tool
        async def send_to_peer(
            peer: Annotated[str, Field(description=f"Peer to ask. Must be one of: {peer_names}.")],
            question: Annotated[str, Field(description="The natural-language question to send to the peer.")],
        ) -> str:
            """Forward a question to a peer agent over A2A.

            Use this when the user's question fits a peer's expertise (per their description) better than
            your own. The reply arrives asynchronously (a human operator answers on the peer's side), so
            this call only *queues* the question and returns immediately.
            """
            peer_url = self._peers.get(peer)
            if peer_url is None:
                return f"Unknown peer {peer!r}. Known peers: {peer_names}."
            qid = str(uuid.uuid4())
            try:
                user_conv_id = current_user_conv_id.get()
            except LookupError:
                logger.warning("send_to_peer called outside a turn; dropping")
                return "Internal error: no active conversation."
            self._state.awaiting_reply[qid] = {"conv_id": user_conv_id, "question": question}
            msg = AskMessage(qid=qid, question=question, sender=self._self_name, reply_url=self._self_a2a_url)
            await send_a2a(peer_url, msg.model_dump())
            return f"Queued question to {peer} (qid {qid[:8]}). Their reply will arrive separately."

        instructions = f"""You are {self._self_name}, a Teams bot assistant.

You should forward questions to peer agents when their expertise fits better than your own.
Peers:
{self._format_peers()}

Guidelines:
- If a peer is a good fit for the user's question, call `send_to_peer` with that peer's name.
- Otherwise, answer the user directly.
- When a peer reply arrives later, you'll see a "[peer update]" note in the conversation; reference it naturally.
- Keep replies short and conversational."""

        # Force local in-memory history. OpenAIChatClient defaults to
        # service-side history (Responses API).
        return Agent(
            client=self._client,
            instructions=instructions,
            tools=[send_to_peer],
            context_providers=[InMemoryHistoryProvider()],
        )

    async def get_agent(self) -> Agent:
        # Per-turn: ensure peer cards are loaded, then build a fresh Agent
        # so its instructions reflect the latest cached descriptions.
        # Agent construction is cheap (config wrapper); the LLM client and
        # session caches are reused across turns.
        await self._refresh_peer_cards()
        return self._build_agent()

    def session_for(self, conv_id: str) -> AgentSession:
        session = self._sessions.get(conv_id)
        if session is None:
            session = AgentSession()
            self._sessions[conv_id] = session
        return session

    def record_peer_reply(self, user_conv_id: str, responder: str, question: str, answer: str) -> None:
        # Append a note to the user's session so the next LLM turn sees it
        # as context. Uses "user" role because most providers accept arbitrary
        # user-role context mid-conversation, while multiple system messages
        # are sometimes rejected.
        session = self._sessions.get(user_conv_id)
        if session is None:
            logger.warning(
                "[%s] no session for user_conv_id=%s; peer reply not recorded", self._self_name, user_conv_id
            )
            return
        note = f"[peer update] {responder} replied: {answer!r} (to your earlier question: {question!r})."
        store = session.state.setdefault(InMemoryHistoryProvider.DEFAULT_SOURCE_ID, {})
        messages: list[Message] = store.setdefault("messages", [])
        messages.append(Message("user", [note]))
