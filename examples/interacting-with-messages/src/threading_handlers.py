"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.apps.utils import get_proactive_thread_reference


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

    conversation_id, thread_root_id = get_proactive_thread_reference(ctx.activity)
    should_quote, is_targeted = variants[text]
    activity = MessageActivityInput(text="This is an explicit proactive threaded reply.")
    if should_quote:
        activity = MessageActivityInput().add_quote(ctx.activity.id, "This threaded reply includes a quote.")
    if is_targeted:
        activity.with_recipient(ctx.activity.from_, is_targeted=True)

    await app.reply(conversation_id, thread_root_id, activity)
    return True
