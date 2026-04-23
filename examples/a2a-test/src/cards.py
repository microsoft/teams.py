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

"""
Adaptive Card builders. The ask card carries its own routing metadata
(qid, sender, reply_url) inside the submit action's data, so the receiving bot
can send the reply back without any in-memory "pending ask" state.
"""
ASK_REPLY_ACTION = "ask_reply"


def ask_card(sender: str, question: str, qid: str, reply_url: str) -> AdaptiveCard:
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
                    .with_data(
                        SubmitData(
                            action=ASK_REPLY_ACTION,
                            data={
                                "qid": qid,
                                "sender": sender,
                                "question": question,
                                "reply_url": reply_url,
                            },
                        )
                    )
                    .with_associated_inputs("auto")
                ]
            ),
            TextBlock(text=f"qid: {qid}", is_subtle=True, size="Small"),
        ],
    )


def reply_card(responder: str, question: str, answer: str, qid: str) -> AdaptiveCard:
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
