"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from contextvars import ContextVar
from os import getenv

from a2a_client import A2APeerClient
from agent_framework import Agent, AgentSession, tool
from agent_framework._sessions import InMemoryHistoryProvider
from agent_framework.openai import OpenAIChatClient
from dotenv import find_dotenv, load_dotenv
from microsoft_teams.apps.plugins.streamer import StreamerProtocol
from types_ import Config, HandoffMessage, TurnIdentity

load_dotenv(find_dotenv(usecwd=True))
logger = logging.getLogger(__name__)

# Per-turn context the handoff_to_peer tool reads.
# main.py sets this before calling agent.run() and resets it after.
current_turn_identity: ContextVar[TurnIdentity | None] = ContextVar("current_turn_identity", default=None)


def _require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"Required environment variable {name!r} is not set.")
    return value


class BotAgent:
    """LLM-backed bot with a single ``handoff_to_peer`` tool.

    Keeps one ``AgentSession`` per Teams conversation so history persists across turns.
    When a peer hands a user off, ``greet_with_handoff`` seeds that session with the
    handoff context and returns the opening message.
    """

    def __init__(self, config: Config, a2a_client: A2APeerClient) -> None:
        self._config = config
        self._a2a_client = a2a_client
        self._llm_client = OpenAIChatClient(
            model=_require_env("AZURE_OPENAI_MODEL"),
            azure_endpoint=_require_env("AZURE_OPENAI_ENDPOINT"),
            api_key=_require_env("AZURE_OPENAI_API_KEY"),
        )
        self._sessions: dict[str, AgentSession] = {}
        # Per-conv locks so concurrent submits don't interleave.
        self._locks: dict[str, asyncio.Lock] = {}
        # Lazily built on first turn after peer card is fetched.
        self._agent: Agent | None = None

    async def _get_or_build_agent(self) -> Agent:
        """Fetch the peer card (once) then build and cache the Agent (once)."""
        if self._agent is None:
            await self._a2a_client.get_peer_card()  # populates cached_card for system prompt
            self._agent = self._build_agent()
        return self._agent

    async def run(
        self, conv_id: str, identity: TurnIdentity, user_text: str, streamer: StreamerProtocol | None = None
    ) -> str:
        """Handle one user turn. Returns the assistant reply text (empty if streamed)."""
        token = current_turn_identity.set(identity)
        try:
            async with self._get_lock(conv_id):
                agent = await self._get_or_build_agent()
                session = self._get_or_create_session(conv_id)
                if streamer is not None:
                    full_text = ""
                    async for chunk in agent.run(user_text, session=session, stream=True):
                        if chunk.text:
                            streamer.emit(chunk.text)
                            full_text += chunk.text
                    return full_text
                response = await agent.run(user_text, session=session)
                return response.text or ""
        finally:
            current_turn_identity.reset(token)

    async def greet_with_handoff(self, conv_id: str, handoff: HandoffMessage) -> str:
        """Seed conversation with handoff context and return the proactive greeting."""
        prompt = (
            f"[handoff context from {handoff.from_}] The user {handoff.user_name} was just handed off to you. "
            f'They asked: "{handoff.summary}". '
            f"Greet them warmly, acknowledge that {handoff.from_} connected you, and answer their question directly."
        )
        # No identity set — the tool's guard prevents a ping-pong handoff.
        async with self._get_lock(conv_id):
            response = await (await self._get_or_build_agent()).run(
                prompt,
                session=self._get_or_create_session(conv_id),
            )
            return response.text or ""

    # ---- internals ----

    def _get_lock(self, conv_id: str) -> asyncio.Lock:
        if conv_id not in self._locks:
            self._locks[conv_id] = asyncio.Lock()
        return self._locks[conv_id]

    def _get_or_create_session(self, conv_id: str) -> AgentSession:
        if conv_id not in self._sessions:
            self._sessions[conv_id] = AgentSession()
        return self._sessions[conv_id]

    def _build_agent(self) -> Agent:
        @tool
        async def handoff_to_peer(summary: str) -> str:
            """Hand off the current user to your peer when their expertise is a better fit.

            Pass a concise summary of the discussion so the peer can pick up cold.
            The peer will then message the user directly.
            """
            identity = current_turn_identity.get()
            if not identity:
                # No identity means we're inside a handoff greeting — prevent ping-pong.
                return "handoff_to_peer is unavailable in this context."
            logger.info(
                "[%s] handoff_to_peer firing → peer=%s user=%s aadId=%s",
                self._config.name,
                self._config.peer_name,
                identity.user_name,
                identity.aad_object_id,
            )
            payload = HandoffMessage(
                from_=self._config.name,
                user_name=identity.user_name,
                aad_object_id=identity.aad_object_id,
                tenant_id=identity.tenant_id,
                service_url=identity.service_url,
                summary=summary,
            )
            try:
                await self._a2a_client.send_handoff(payload)
            except Exception as exc:  # noqa: BLE001
                logger.exception("[%s] handoff_to_peer FAILED: %s", self._config.name, exc)
                return f"Handoff failed: {exc}"
            logger.info("[%s] handoff_to_peer OK", self._config.name)
            return "Handoff confirmed. The peer will message the user directly."

        return Agent(
            client=self._llm_client,
            instructions=self._build_system_prompt(),
            tools=[handoff_to_peer],
            context_providers=[InMemoryHistoryProvider()],
        )

    def _build_system_prompt(self) -> str:
        peer_card = self._a2a_client.cached_card
        peer_desc = (
            peer_card.description
            if peer_card
            else f"(peer card not yet loaded; configured name: {self._config.peer_name})"
        )
        return "\n".join(
            [
                f"You are {self._config.name}, a Teams bot. Your specialty: {self._config.description}.",
                "",
                "You have one peer:",
                f"- {self._config.peer_name}: {peer_desc}",
                "",
                "Guidelines:",
                f"- If the user's question fits {self._config.peer_name}'s specialty better than your own, "
                "call handoff_to_peer with a clear summary. Then briefly tell the user you're handing them over.",
                "- Otherwise, answer directly.",
                '- If you see a "[handoff context from X]" note, the previous bot has already connected the user '
                "with you and described their question — greet the user warmly, briefly mention X sent them, "
                'and answer the question directly in the same message. Don\'t just ask "how can I help?" — '
                "the question is already in the context.",
                "- Keep replies short and conversational.",
            ]
        )
