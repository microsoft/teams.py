"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.cards import (
    ActionSet,
    AdaptiveCard,
    ExecuteAction,
    SubmitData,
    TextBlock,
)
from microsoft_teams.cards.core import TextInput

# Adaptive Card builders. The ask card's submit returns only `qid`; the bot
# resolves reply routing from server state (card data is client-tamperable).
ASK_REPLY_ACTION = "ask_reply"


def ask_card(sender: str, question: str, qid: str) -> AdaptiveCard:
    # Shown to the operator of the receiving bot. Operator types an answer
    # and clicks Send reply, which fires an Action.Execute back to the bot.
    return AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        version="1.4",
        body=[
            TextBlock(text=f"From {sender}", weight="Bolder", size="Medium"),
            TextBlock(text=question, wrap=True),
            TextInput(id="answer").with_label("Your answer").with_placeholder("Type here…"),
            ActionSet(
                actions=[
                    ExecuteAction(title="Send reply")
                    .with_data(SubmitData(action=ASK_REPLY_ACTION, data={"qid": qid}))
                    .with_associated_inputs("auto")
                ]
            ),
            TextBlock(text=f"qid: {qid}", is_subtle=True, size="Small"),
        ],
    )


def reply_card(responder: str, question: str, answer: str, qid: str) -> AdaptiveCard:
    # Shown to the user who originally asked, once the peer's operator has
    # answered. Display-only — no submit action.
    return AdaptiveCard(
        schema="http://adaptivecards.io/schemas/adaptive-card.json",
        version="1.4",
        body=[
            TextBlock(text=f"{responder} replies", weight="Bolder", size="Medium"),
            TextBlock(text=f"You asked: {question}", is_subtle=True, wrap=True),
            TextBlock(text=answer, wrap=True),
            TextBlock(text=f"qid: {qid}", is_subtle=True, size="Small"),
        ],
    )
