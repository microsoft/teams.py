"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App, to_threaded_conversation_id


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
    """Construct a threaded conversation ID manually when the command matches."""
    if text != "thread manual":
        return False
    conversation_id, thread_root_id = _thread_reference(ctx)
    thread_id = to_threaded_conversation_id(conversation_id, thread_root_id)
    await app.send(thread_id, "This was sent using to_threaded_conversation_id() + app.send() for manual control.")
    return True


def _thread_reference(ctx: ActivityContext[MessageActivity]) -> tuple[str, str]:
    conversation_id = ctx.conversation_ref.conversation.id
    parts = conversation_id.split(";messageid=")
    return conversation_id, parts[1] if len(parts) > 1 else ctx.activity.id
