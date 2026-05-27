"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from contextvars import ContextVar
from typing import Annotated

from agent_framework import tool
from microsoft_teams.cards import AdaptiveCard, Choice, ChoiceSetInput, ExecuteAction, SubmitData, TextBlock
from pydantic import Field

# Per-turn card bucket. main.py sets a fresh list at the start of each handler so concurrent turns
# don't clobber each other. The tool appends into whichever list is active in its context.
pending_cards: ContextVar[list[AdaptiveCard] | None] = ContextVar("pending_cards", default=None)

CLARIFICATION_VERB = "clarification"
CLARIFICATION_INPUT_ID = "clarificationChoice"


@tool
async def request_clarification(
    question: Annotated[str, Field(description="The clarification question to ask the user.")],
    options: Annotated[list[str], Field(description="2-4 candidate interpretations the user can pick between.")],
) -> str:
    """Show an Adaptive Card asking the user to clarify their ambiguous request.

    The user picks one option and submits; their choice arrives as the next card-action turn.
    """
    cards = pending_cards.get()
    if cards is None:
        return "No active turn context; card could not be attached."
    card = (
        AdaptiveCard(version="1.6")
        .with_body(
            [
                TextBlock(text=question, weight="Bolder", size="Medium", wrap=True),
                ChoiceSetInput(
                    id=CLARIFICATION_INPUT_ID,
                    choices=[Choice(title=o, value=o) for o in options],
                    is_required=True,
                ),
            ]
        )
        .with_actions(
            [
                ExecuteAction(title="Submit")
                .with_data(SubmitData(CLARIFICATION_VERB, {CLARIFICATION_INPUT_ID: ""}))
                .with_associated_inputs("auto"),
            ]
        )
    )
    cards.append(card)
    return "Clarification card attached."


tools = [request_clarification]
