"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Agent 365 Reactive Example
# ==========================
# This example echoes messages back as the concrete AgentUser from the inbound activity.

import asyncio
import logging
import re

from microsoft_teams.api import AdaptiveCardInvokeActivity, MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.api.models.adaptive_card import AdaptiveCardActionMessageResponse
from microsoft_teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()


@app.on_message_pattern(re.compile(r"hello|hi|greetings"))
async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle greeting messages as the inbound agent user."""
    await ctx.reply("Hello! How can I assist you today?")


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Echo incoming messages as the inbound agent user."""
    logger.info(f"[Agent365 onMessage] Message received: {ctx.activity.text}")
    logger.info(f"[Agent365 onMessage] From: {ctx.activity.from_}")
    logger.info(f"[Agent365 onMessage] Agent user: {ctx.agent_user}")

    await ctx.reply(TypingActivityInput())

    if "reply" in ctx.activity.text.lower():
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


@app.on_card_action_execute("ack_agent365_card")
async def handle_agent365_card_ack(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle the Action.Execute button from the proactive AgentUser card."""
    data = ctx.activity.value.action.data
    logger.info(f"[Agent365 card] Acknowledged with data: {data}")
    await ctx.send(f"Acknowledged Agent 365 card. Data: {data}")
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Acknowledged",
    )


if __name__ == "__main__":
    asyncio.run(app.start())
