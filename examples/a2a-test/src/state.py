"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BotState:
    """In-memory state for one bot. Single-process; fine for a sample."""

    name: str
    # Conversation id of the last Teams user to DM this bot — the human
    # operator who will answer incoming A2A asks.
    operator_conv_id: Optional[str] = None

    # Asks this bot initiated, keyed by qid. Each value: {conv_id, question}.
    # When the peer's reply lands, we pop the qid and push the reply card into
    # the stashed conversation.
    awaiting_reply: dict[str, dict[str, Any]] = field(default_factory=dict[str, dict[str, Any]])
