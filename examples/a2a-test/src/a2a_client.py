"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import uuid
from typing import Any
from urllib.parse import urlsplit

import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import DataPart, Message, Part, Role

# Outbound A2A helpers + peer URL allowlist check.

_DEFAULT_PORTS = {"http": 80, "https": 443}


def _origin(url: str) -> tuple[str, str, int] | None:
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    if not scheme or not host:
        return None
    port = parts.port if parts.port is not None else _DEFAULT_PORTS.get(scheme, 0)
    return (scheme, host, port)


def is_allowed_peer(url: str, allowed: list[str]) -> bool:
    # Match by scheme/host/port so a trailing slash or default port
    # doesn't flip a valid peer to invalid.
    target = _origin(url)
    if target is None:
        return False
    for candidate in allowed:
        candidate_origin = _origin(candidate)
        if candidate_origin is not None and candidate_origin == target:
            return True
    return False


async def send_a2a(peer_url: str, data: dict[str, Any]) -> None:
    # Resolve the peer's agent card, build an a2a-sdk client, and fire a
    # single DataPart-carrying message. We drain the response stream
    # without reading it — the peer only sends an `ack`; any "real"
    # answer comes later as a separate inbound A2A call back to us.
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
