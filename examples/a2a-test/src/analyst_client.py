"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import uuid
from typing import Any, cast

import httpx
from a2a.client import Client, ClientConfig, ClientFactory, minimal_agent_card
from a2a.types import Message as A2AMessage
from a2a.types import Part, Role, Task, TextPart, TransportProtocol
from data_analyst import AGENT_PATH as DATA_ANALYST_PATH

logger = logging.getLogger(__name__)

_http_client: httpx.AsyncClient | None = None
_client: Client | None = None


def _get_client(base_url: str) -> Client:
    global _http_client, _client
    if _client is None:
        _http_client = httpx.AsyncClient(timeout=60.0)
        cfg = ClientConfig(
            httpx_client=_http_client,
            supported_transports=[TransportProtocol.jsonrpc],
        )
        card = minimal_agent_card(f"{base_url}{DATA_ANALYST_PATH}/", [TransportProtocol.jsonrpc])
        _client = ClientFactory(cfg).create(card)
    return _client


async def ask(base_url: str, query: str, context_id: str | None) -> tuple[list[dict[str, Any]], str]:
    """Send a query to the data-analyst A2A server.

    Returns (cards, text). `cards` is the list of Adaptive Card dicts extracted from DataParts;
    `text` is the analyst's text reply. Passing a stable `context_id` lets the analyst keep a
    per-conversation session on the server side.
    """
    msg = A2AMessage(
        role=Role.user,
        parts=[Part(root=TextPart(kind="text", text=query))],
        message_id=uuid.uuid4().hex,
        context_id=context_id,
    )

    cards: list[dict[str, Any]] = []
    text: str = ""

    def _collect(parts: list[Part]) -> None:
        nonlocal text
        for part in parts:
            if part.root.kind == "data":
                card_list = part.root.data.get("cards")
                if isinstance(card_list, list):
                    cards.extend(cast(dict[str, Any], c) for c in card_list if isinstance(c, dict))  # type: ignore
            elif part.root.kind == "text" and part.root.text:
                text = part.root.text

    async for item in _get_client(base_url).send_message(msg):
        if isinstance(item, A2AMessage):
            _collect(item.parts)
            continue
        task: Task = item[0]
        if task.status.message is not None:
            _collect(task.status.message.parts)
        for artifact in task.artifacts or []:
            _collect(artifact.parts)

    return cards, text
