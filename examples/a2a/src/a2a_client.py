"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import uuid

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import AgentCard, DataPart, Message, MessageSendParams, Part, Role, SendMessageRequest
from types_ import Config, HandoffMessage

logger = logging.getLogger(__name__)


class A2APeerClient:
    """Outbound A2A. Resolves the peer's AgentCard once, then ships HandoffMessage DataParts."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._cached_card: AgentCard | None = None
        self._init_task: asyncio.Task[AgentCard] | None = None

    @property
    def cached_card(self) -> AgentCard | None:
        return self._cached_card

    async def get_peer_card(self) -> AgentCard:
        """Fetch (and cache) the peer's AgentCard via its well-known endpoint."""
        if self._cached_card:
            return self._cached_card
        if self._init_task is None:
            self._init_task = asyncio.create_task(self._resolve())
        try:
            return await self._init_task
        except Exception:
            # Don't cache the failure — a peer that wasn't up yet should resolve
            # on the next attempt instead of failing for the process lifetime.
            self._init_task = None
            logger.warning("Failed to resolve peer AgentCard at %s; will retry on next call", self._config.peer_url)
            raise

    async def send_handoff(self, payload: HandoffMessage) -> None:
        """Ship a HandoffMessage as an A2A DataPart to the peer."""
        if not self._cached_card:
            await self.get_peer_card()
        async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as http_client:
            client = A2AClient(httpx_client=http_client, agent_card=self._cached_card)
            request = SendMessageRequest(
                id=str(uuid.uuid4()),
                params=MessageSendParams(
                    message=Message(
                        message_id=str(uuid.uuid4()),
                        role=Role.user,
                        parts=[Part(root=DataPart(data=payload.model_dump(by_alias=True)))],
                    )
                ),
            )
            await client.send_message(request)

    async def _resolve(self) -> AgentCard:
        base_url = self._config.peer_url.rstrip("/") + "/a2a"
        logger.info("Resolving peer AgentCard at %s", base_url)
        async with httpx.AsyncClient(timeout=10.0) as http:
            card = await A2ACardResolver(httpx_client=http, base_url=base_url).get_agent_card()
        self._cached_card = card
        return card
