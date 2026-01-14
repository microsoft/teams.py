"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Targeted Messages Example

This example demonstrates how to send targeted (private) messages
to specific users in Microsoft Teams group chats and channels.
"""

import asyncio
import re

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App

app = App()


@app.on_message_pattern(re.compile(r"^targeted-update$", re.IGNORECASE))
async def on_targeted_update(ctx: ActivityContext[MessageActivity]) -> None:
    """Send a targeted message and then update it."""
    # Send initial targeted message
    sent = await ctx.send(
        "⏳ This private message will be updated in 3 seconds...",
        targeted_recipient_id=ctx.activity.from_.id,
    )

    # Wait 3 seconds
    await asyncio.sleep(3)

    # Update the targeted message
    update_activity = MessageActivityInput(
        id=sent.id,
        text="✅ Private message has been updated! Only you can see this.",
    )
    update_activity.recipient = ctx.activity.from_

    conversation_id = ctx.activity.conversation.id
    await ctx.api.conversations.activities(conversation_id).update(sent.id, update_activity, is_targeted=True)


@app.on_message_pattern(re.compile(r"^targeted-delete$", re.IGNORECASE))
async def on_targeted_delete(ctx: ActivityContext[MessageActivity]) -> None:
    """Send a targeted message and then delete it."""
    # Send initial targeted message
    sent = await ctx.send(
        "⏳ This private message will be deleted in 3 seconds...",
        targeted_recipient_id=ctx.activity.from_.id,
    )

    # Wait 3 seconds
    await asyncio.sleep(3)

    # Delete the targeted message
    conversation_id = ctx.activity.conversation.id
    await ctx.api.conversations.activities(conversation_id).delete(sent.id, is_targeted=True)

    # Send confirmation (also targeted)
    await ctx.send(
        "🗑️ The previous private message has been deleted!",
        targeted_recipient_id=ctx.activity.from_.id,
    )


@app.on_message_pattern(re.compile(r"^targeted-reply$", re.IGNORECASE))
async def on_targeted_reply(ctx: ActivityContext[MessageActivity]) -> None:
    """Reply with a targeted message that only the sender can see."""
    await ctx.reply(
        "🔒 This private reply is only visible to you!",
        targeted_recipient_id=ctx.activity.from_.id,
    )


@app.on_message_pattern(re.compile(r"^targeted$", re.IGNORECASE))
async def on_targeted_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Send a targeted message that only the sender can see."""
    await ctx.send(
        "👋 This is a private message only you can see!",
        targeted_recipient_id=ctx.activity.from_.id,
    )


@app.on_message
async def on_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Default handler - show available commands."""
    await ctx.send(
        "**Targeted Messages Example**\n\n"
        "Available commands:\n"
        "- `targeted` - Send a private message only you can see\n"
        "- `targeted-reply` - Reply privately to your message\n"
        "- `targeted-update` - Send a private message, then update it\n"
        "- `targeted-delete` - Send a private message, then delete it\n\n"
        "Try one of these commands in a group chat or channel!"
    )


if __name__ == "__main__":
    asyncio.run(app.start())
