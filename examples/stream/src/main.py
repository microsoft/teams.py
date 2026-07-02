"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from random import random

from microsoft_teams.api import CardAction, CardActionType, MessageActivity, MessageActivityInput, SuggestedActions
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.cards import AdaptiveCard

# Surface SDK INFO/WARNING logs (including the anonymous-mode startup warning
# emitted when CLIENT_ID / CLIENT_SECRET / TENANT_ID are not configured).
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()

# List of sample messages to emit
STREAM_MESSAGES = [
    "🚀 App installation detected! Starting stream...",
    "📊 Initializing data streams...",
    "✅ Connection established",
    "🔄 Processing background tasks...",
    "📈 System metrics looking good",
    "💡 Ready to assist you!",
    "🌟 All systems operational",
    "📋 Checking configurations...",
    "🔧 Optimizing performance...",
    "✨ Stream test complete!",
]

FIRST_STREAM_MESSAGES = [
    "[stream 1] Starting the first streamed response. ",
    "[stream 1] This is using the default ctx.stream instance. ",
    "[stream 1] Next the handler will close the current streamed message.",
]

SECOND_STREAM_MESSAGES = [
    "[stream 2] Reusing ctx.stream after emit reopens the closed stream. ",
    "[stream 2] This should render after the non-stream checkpoint message. ",
    "[stream 2] The app processor will close this stream when the handler returns.",
]


def should_run_multi_stream(text: str | None) -> bool:
    normalized = (text or "").lower().replace("-", " ")
    return "multi stream" in normalized


def should_send_simple_card(text: str | None) -> bool:
    normalized = (text or "").lower().replace("-", " ")
    return "simple card" in normalized


def create_simple_card() -> AdaptiveCard:
    return AdaptiveCard.model_validate(
        {
            "type": "AdaptiveCard",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "Simple Adaptive Card",
                    "weight": "Bolder",
                    "size": "Large",
                    "wrap": True,
                },
                {
                    "type": "TextBlock",
                    "text": "If you can see this card, basic Adaptive Card delivery is working.",
                    "wrap": True,
                },
            ],
        }
    )


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Stream messages to the user on any message activity."""

    if should_send_simple_card(ctx.activity.text):
        sent_card = await ctx.send(
            MessageActivityInput(text="Sending a simple Adaptive Card.").add_card(create_simple_card())
        )
        logger.info("Sent simple adaptive card: %s", sent_card.id)
        return

    if should_run_multi_stream(ctx.activity.text):
        ctx.stream.update("Starting stream 1...")
        await asyncio.sleep(1)

        for message in FIRST_STREAM_MESSAGES:
            await asyncio.sleep(0.5)
            ctx.stream.emit(message)

        card_message = MessageActivityInput(text="Adaptive Card emitted as part of stream 1.").add_card(
            create_simple_card()
        )
        ctx.stream.emit(card_message)
        sent_message = await ctx.stream.close()
        if sent_message:
            logger.info("Sent stream 1 final message with adaptive card: %s", sent_message.id)
        await asyncio.sleep(2)

        ctx.stream.update("Starting stream 2...")
        await asyncio.sleep(1)

        for message in SECOND_STREAM_MESSAGES:
            await asyncio.sleep(0.5)
            ctx.stream.emit(message)
        return

    ctx.stream.update("Stream starting...")
    await asyncio.sleep(1)

    # Stream messages with delays using ctx.stream.emit
    for message in STREAM_MESSAGES:
        await asyncio.sleep(random())
        ctx.stream.emit(message)

    # Add suggested actions to the final message
    ctx.stream.emit(
        MessageActivityInput().with_suggested_actions(
            SuggestedActions(
                to=[ctx.activity.from_.id],
                actions=[
                    CardAction(type=CardActionType.IM_BACK, title="Run again", value="Run again"),
                    CardAction(type=CardActionType.IM_BACK, title="Show status", value="Show status"),
                    CardAction(type=CardActionType.IM_BACK, title="Help", value="Help"),
                ],
            )
        )
    )


if __name__ == "__main__":
    asyncio.run(app.start())
