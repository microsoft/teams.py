"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import re

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.message import MessageActivityInput
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

# Surface SDK INFO/WARNING logs (including the anonymous-mode startup warning
# emitted when CLIENT_ID / CLIENT_SECRET / TENANT_ID are not configured).
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App()


@app.on_message_pattern(re.compile(r"hello|hi|greetings"))
async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
    """Handle greeting messages."""
    await ctx.reply("Hello! How can I assist you today?")


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    logger.info(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    logger.info(f"[GENERATED onMessage] From: {ctx.activity.from_}")
    await ctx.reply(TypingActivityInput())

    if "extended" in ctx.activity.text.lower():
        rich_content = "\n".join([
            "# Extended Markdown Demo",
            "",
            "## Table",
            "| Feature | Status |",
            "|---------|--------|",
            "| Tables  | Supported |",
            "| Math    | Supported |",
            "",
            "## Math",
            "$$E = mc^2$$",
        ])
        reply = MessageActivityInput(text=rich_content).with_text_format("extendedmarkdown")
        await ctx.reply(reply)
    elif "reply" in ctx.activity.text.lower():
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


if __name__ == "__main__":
    asyncio.run(app.start())
