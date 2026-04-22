"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from contextvars import ContextVar
from typing import Annotated

from agent_framework import tool
from microsoft_teams.cards import AdaptiveCard, Fact, FactSet, TextBlock
from pydantic import Field

# Per-turn card bucket. main.py sets a fresh list at the start of each handler so concurrent turns
# don't clobber each other. The tool appends into whichever list is active in its context.
pending_cards: ContextVar[list[AdaptiveCard] | None] = ContextVar("pending_cards", default=None)


@tool
async def send_welcome_card(
    greeting: Annotated[str, Field(description="The greeting message for the user. eg Hello, John! or Welcome!")],
) -> str:
    """Attach a welcome card with a capabilities overview."""
    card = AdaptiveCard(version="1.5").with_body(
        [
            TextBlock(text=f"{greeting} Here are some things I can do:", size="Large", weight="Bolder", wrap=True),
            FactSet(
                facts=[
                    Fact(title="Docs", value="Microsoft Learn search with citations"),
                    Fact(title="Streaming", value="Token-by-token replies"),
                    Fact(title="Memory", value="Per-conversation context"),
                    Fact(title="Feedback", value="Thumbs up/down with a follow-up form"),
                ]
            ),
        ]
    )
    cards = pending_cards.get()
    if cards is None:
        return "No active turn context; card could not be attached."
    cards.append(card)
    return "Card attached."


tools = [send_welcome_card]
