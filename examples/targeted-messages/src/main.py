"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

"""
Example: Targeted Messages

A bot that demonstrates targeted (ephemeral) messages in Microsoft Teams.
Targeted messages are only visible to a specific recipient - other participants
in the conversation won't see them.
"""

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities."""
    await ctx.reply(TypingActivityInput())

    text = (ctx.activity.text or "").lower()

    # ============================================
    # Test targeted UPDATE
    # ============================================
    if "test update" in text:
        # First send a targeted message
        targeted_message = MessageActivityInput(text="🔒 [UPDATE] Original targeted message...").with_recipient(
            ctx.activity.from_, is_targeted=True
        )

        result = await ctx.send(targeted_message)
        print(f"Initial targeted message ID: {result.id}")

        # Wait then update
        async def update_after_delay():
            await asyncio.sleep(3)
            try:
                # For targeted updates, do not include recipient in the payload.
                updated_message = MessageActivityInput(
                    text="🔒 [UPDATE] ✅ UPDATED targeted message! (only you see this)"
                )
                updated_message.id = result.id

                await ctx.api.conversations.activities(ctx.activity.conversation.id).update_targeted(
                    result.id, updated_message
                )
                print("Targeted UPDATE completed")
            except Exception as err:
                print(f"Targeted UPDATE error: {err}")

        asyncio.create_task(update_after_delay())
        return

    # ============================================
    # Test targeted DELETE
    # ============================================
    if "test delete" in text:
        # First send a targeted message
        targeted_message = MessageActivityInput(
            text="🔒 [DELETE] This targeted message will be DELETED in 5 seconds..."
        ).with_recipient(ctx.activity.from_, is_targeted=True)

        result = await ctx.send(targeted_message)
        print(f"Targeted message to delete, ID: {result.id}")

        # Wait then delete using the targeted API
        async def delete_after_delay():
            await asyncio.sleep(5)
            try:
                await ctx.api.conversations.activities(ctx.activity.conversation.id).delete_targeted(result.id)
                print("Targeted DELETE completed")
            except Exception as err:
                print(f"Targeted DELETE error: {err}")

        asyncio.create_task(delete_after_delay())
        return

    # ============================================
    # Test public reply
    # Everyone in the chat sees the reply.
    # ============================================
    if "test public" in text:
        await ctx.send(MessageActivityInput(text="📋 Here is the public result — everyone can see this!"))
        return

    # ============================================
    # Test targeted SEND
    # ============================================
    if "test send" in text:
        targeted_reply = MessageActivityInput(
            text="This is a **targeted message** — only YOU can see this!"
        ).with_recipient(ctx.activity.from_, is_targeted=True)
        await ctx.send(targeted_reply)
        return

    # ============================================
    # Help / Default
    # ============================================
    await ctx.reply(
        "**Targeted Messages Test Bot**\n\n"
        "**Commands:**\n"
        "- `test send` - Send a targeted message\n"
        "- `test update` - Send a targeted message, then update it after 3 seconds\n"
        "- `test delete` - Send a targeted message, then delete it after 5 seconds\n"
        "- `test public` - Send a public message (visible to all)\n\n"
        "💡 *Test in a group chat to verify others don't see targeted messages!*"
    )


if __name__ == "__main__":
    asyncio.run(app.start())
