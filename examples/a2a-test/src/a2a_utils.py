"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
from typing import Any, cast

from agent_framework import AgentResponse

logger = logging.getLogger(__name__)


def _raw_kinds(raw: Any) -> list[str]:
    items = cast(list[Any], raw) if isinstance(raw, list) else [raw]
    return [str(getattr(r, "kind", "")) for r in items]


def extract_cards(response: AgentResponse[Any]) -> list[dict[str, Any]]:
    """Extract Adaptive Card dicts from the A2A DataPart the server wraps cards in."""
    cards: list[dict[str, Any]] = []
    for msg in response.messages:
        for content in msg.contents:
            if "data" not in _raw_kinds(content.raw_representation):
                continue
            try:
                data = json.loads(content.text or "{}")
            except (json.JSONDecodeError, TypeError):
                logger.warning("extract_cards: failed to parse data part: %r", content.text)
                continue
            if not isinstance(data, dict):
                continue
            payload = cast(dict[str, Any], data)
            card_list = payload.get("cards")
            if isinstance(card_list, list):
                for c in cast(list[Any], card_list):
                    if isinstance(c, dict):
                        cards.append(cast(dict[str, Any], c))
            else:
                single = payload.get("card")
                if isinstance(single, dict):
                    cards.append(cast(dict[str, Any], single))
    return cards
