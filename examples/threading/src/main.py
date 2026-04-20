"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App, to_threaded_conversation_id

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities."""
    await ctx.reply(TypingActivityInput())

    text = (ctx.activity.text or "").lower()
    conversation_id = ctx.conversation_ref.conversation.id
    message_id = ctx.activity.id

    # When inside a thread, conversation_id contains ;messageid=<rootId>.
    # Extract the root ID for threading; for top-level messages, use activity.id.
    parts = conversation_id.split(";messageid=")
    thread_root_id = parts[1] if len(parts) > 1 else message_id

    # ============================================
    # context.reply() — reactive threaded reply
    # ============================================
    if "test reply" in text:
        await ctx.reply("This is a threaded reply to your message.")
        return

    # ============================================
    # context.send() — reactive send to same thread
    # ============================================
    if "test send" in text:
        await ctx.send("This is sent to the same thread, without quoting.")
        return

    # ============================================
    # app.reply() — proactive threaded reply
    # ============================================
    if "test proactive" in text:
        await app.reply(conversation_id, thread_root_id, "This is a proactive threaded reply using app.reply().")
        return

    # ============================================
    # to_threaded_conversation_id() + app.send() — advanced manual control (channels only)
    # ============================================
    if "test manual" in text:
        # to_threaded_conversation_id() is only valid for conversations that support threading
        base = conversation_id.split(";")[0]
        threading_suffixes = ("@thread.tacv2", "@thread.skype", "@unq.gbl.spaces")
        if not any(base.endswith(s) for s in threading_suffixes):
            await ctx.reply("This command doesn't support threading in this conversation type.")
            return
        thread_id = to_threaded_conversation_id(conversation_id, thread_root_id)
        await app.send(thread_id, "This was sent using to_threaded_conversation_id() + app.send() for manual control.")
        return

    # ============================================
    # Help / Default
    # ============================================
    if "help" in text:
        await ctx.reply(
            "**Threading Test Bot**\n\n"
            "**Commands:**\n"
            "- `test reply` - ctx.reply() reactive threaded reply\n"
            "- `test send` - ctx.send() to same thread without quoting\n"
            "- `test proactive` - app.reply() proactive threaded reply\n"
            "- `test manual` - to_threaded_conversation_id() + app.send() for advanced control"
        )
        return

    await ctx.send('Say "help" for available commands.')


if __name__ == "__main__":
    asyncio.run(app.start())
