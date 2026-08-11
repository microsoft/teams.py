"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App
from quoting import (
    handle_quote_add,
    handle_quote_batch,
    handle_quote_manual,
    handle_quote_message,
    handle_quote_reply,
    handle_quoted_message,
)
from reactions import handle_add_reaction, handle_proactive_reaction, handle_remove_reaction
from threading_handlers import handle_manual_thread, handle_proactive_thread, handle_thread_reply, handle_thread_send

logging.basicConfig(level=logging.INFO)

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Dispatch message interaction commands to focused handlers."""
    await ctx.send(TypingActivityInput())
    ctx.activity.strip_mentions_text()
    text = (ctx.activity.text or "").strip().lower()
    handled_quoted_message = await handle_quoted_message(ctx)

    handlers = (
        handle_quote_reply,
        handle_quote_message,
        handle_quote_add,
        handle_quote_batch,
        handle_quote_manual,
        handle_thread_reply,
        handle_thread_send,
        handle_add_reaction,
        handle_remove_reaction,
    )
    for handler in handlers:
        if await handler(ctx, text):
            return

    app_handlers = (
        handle_proactive_thread,
        handle_manual_thread,
        handle_proactive_reaction,
    )
    for handler in app_handlers:
        if await handler(app, ctx, text):
            return

    if handled_quoted_message:
        return

    if text == "help":
        await ctx.send(
            "**Interacting with Messages**\n\n"
            "**Quoting:**\n"
            "- `quote reply` - auto-quote your message\n"
            "- `quote message` - quote a previously sent message\n"
            "- `quote add` - compose a quote with the message builder\n"
            "- `quote batch` - combine multiple quotes\n"
            "- `quote manual` - combine a quote and text manually\n\n"
            "**Threading:**\n"
            "- `thread reply` - send a reactive threaded reply\n"
            "- `thread send` - send to the same thread without quoting\n"
            "- `thread proactive` - send a proactive threaded reply\n"
            "- `thread manual` - construct a threaded conversation ID manually\n\n"
            "**Reactions:**\n"
            "- `reaction add <type>` - add a reaction to your message\n"
            "- `reaction remove <type>` - add, then remove, a reaction\n"
            "- `reaction proactive` - send a bot message and react to it using app-level APIs\n\n"
            "Quote or react to one of my messages to see the corresponding inbound event."
        )
        return

    await ctx.send('Say "help" for available commands.')


if __name__ == "__main__":
    asyncio.run(app.start())
