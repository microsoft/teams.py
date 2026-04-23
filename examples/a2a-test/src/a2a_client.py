"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import uuid
from typing import Any

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import DataPart, Message, Part, Role

# Outbound A2A sender. Resolves the peer's agent card, creates an a2a-sdk
# client, and fires a single `DataPart`-carrying message. We drain the
# response stream without caring about the body — the peer only sends an
# `ack`, the real reply comes later asynchronously over the peer's own A2A
# call back to us.


async def send_a2a(peer_url: str, data: dict[str, Any]) -> None:
    async with httpx.AsyncClient(timeout=60.0) as http_client:
        peer_card = await A2ACardResolver(httpx_client=http_client, base_url=peer_url).get_agent_card()
        factory = ClientFactory(ClientConfig(httpx_client=http_client, streaming=True))
        client = factory.create(peer_card)

        request = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=DataPart(data=data))],
        )
        async for _ in client.send_message(request):
            pass
