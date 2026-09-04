"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.apps.utils.thread import parse_threaded_conversation_id


async def handle_default_send(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Use the default reactive placement for the inbound scope."""
    if text != "default send":
        return False
    await ctx.send("This uses the default reactive placement for the current conversation.")
    return True


async def handle_proactive_thread(app: App, ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send one of the explicit proactive thread-placement variants."""
    variants = {
        "thread proactive": (False, False),
        "thread proactive quote": (True, False),
        "thread proactive targeted": (False, True),
        "thread proactive targeted quote": (True, True),
    }
    if text not in variants:
        return False

    conversation_id, thread_root_id = _thread_reference(ctx)
    should_quote, is_targeted = variants[text]
    activity = MessageActivityInput(text="This is an explicit proactive threaded reply.")
    if should_quote:
        activity = MessageActivityInput().add_quote(ctx.activity.id, "This threaded reply includes a quote.")
    if is_targeted:
        activity.with_recipient(ctx.activity.from_, is_targeted=True)

    await app.reply(conversation_id, thread_root_id, activity)
    return True


def _thread_reference(ctx: ActivityContext[MessageActivity]) -> tuple[str, str]:
    conversation_id = ctx.conversation_ref.conversation.id
    thread = ctx.activity.channel_data.thread if ctx.activity.channel_data else None
    base_conversation_id, legacy_thread_root_id = parse_threaded_conversation_id(conversation_id)
    thread_root_id = thread.id if thread and thread.id else legacy_thread_root_id or ctx.activity.id
    return base_conversation_id, thread_root_id
