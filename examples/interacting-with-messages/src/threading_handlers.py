"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App


async def handle_thread_reply(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send a reactive threaded reply when the command matches."""
    if text != "thread reply":
        return False
    await ctx.reply("This is a threaded reply to your message.")
    return True


async def handle_thread_send(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send to the current thread without quoting when the command matches."""
    if text != "thread send":
        return False
    await ctx.send("This is sent to the same thread, without quoting.")
    return True


async def handle_proactive_thread(app: App, ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send a proactive threaded reply when the command matches."""
    if text != "thread proactive":
        return False
    conversation_id, thread_root_id = _thread_reference(ctx)
    await app.reply(conversation_id, thread_root_id, "This is a proactive threaded reply using app.reply().")
    return True


async def handle_manual_thread(app: App, ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send to an explicitly selected thread root when the command matches."""
    if text != "thread manual":
        return False
    conversation_id, thread_root_id = _thread_reference(ctx)
    await app.reply(conversation_id, thread_root_id, "This was sent using app.reply() with an explicit thread root.")
    return True


def _thread_reference(ctx: ActivityContext[MessageActivity]) -> tuple[str, str]:
    conversation_id = ctx.conversation_ref.conversation.id
    thread = ctx.activity.channel_data.thread if ctx.activity.channel_data else None
    return conversation_id, thread.id if thread and thread.id else ctx.activity.id
