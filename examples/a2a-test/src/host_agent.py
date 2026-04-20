"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import os
from typing import Annotated, Any, cast

from agent_framework import Agent, FunctionInvocationContext, tool
from agent_framework.foundry import FoundryChatClient
from agent_framework_a2a import A2AAgent  # type: ignore[import-untyped]
from azure.identity.aio import ClientSecretCredential
from kb_agent import AGENT_PATH as KB_AGENT_PATH
from prompts import HOST_INSTRUCTIONS

logger = logging.getLogger(__name__)

KB_AGENT_URL = os.getenv("KB_AGENT_URL", f"http://localhost:3979{KB_AGENT_PATH}/")

_kb_agent = A2AAgent(url=KB_AGENT_URL)


def _extract_cards(response: Any) -> list[dict[str, Any]]:
    """Walk an A2AAgent response for DataParts carrying Adaptive Card dicts."""
    cards: list[dict[str, Any]] = []
    for msg in response.messages:
        for content in msg.contents:
            raw = content.raw_representation
            if raw is None or getattr(raw, "kind", None) != "data":
                continue
            data = cast(dict[str, Any], getattr(raw, "data", {}) or {})
            card_list = cast(list[Any], data.get("cards") or [])
            cards.extend(cast(dict[str, Any], c) for c in card_list if isinstance(c, dict))
    return cards


@tool
async def ask_kb(
    question: Annotated[str, "The user's question, phrased as-is for the KB agent."],
    context: FunctionInvocationContext,
) -> str:
    """Ask the knowledge-base agent a question about Northwind Co. internal policies/handbooks."""
    logger.info("ask_kb: q=%r", question)
    response = await _kb_agent.run(question)
    cards = _extract_cards(response)
    if context.session is not None and cards:
        context.session.state.setdefault("cards", []).extend(cards)
    logger.info("ask_kb: new_cards=%d", len(cards))
    return f"{len(cards)} card(s) rendered." if cards else (response.text or "No answer.")


host_agent = Agent(
    FoundryChatClient(
        credential=ClientSecretCredential(
            tenant_id=os.environ["TENANT_ID"],
            client_id=os.environ["CLIENT_ID"],
            client_secret=os.environ["CLIENT_SECRET"],
        ),
    ),
    instructions=HOST_INSTRUCTIONS,
    tools=[ask_kb],
)
