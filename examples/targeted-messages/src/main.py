"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.devtools import DevToolsPlugin

"""
Example: Targeted Messages

A bot that demonstrates targeted (ephemeral) messages in Microsoft Teams.
Targeted messages are only visible to a specific recipient - other participants
in the conversation won't see them.
"""

app = App(plugins=[DevToolsPlugin()])


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities."""
    await ctx.reply(TypingActivityInput())

    text = (ctx.activity.text or "").lower()

    # ============================================
    # Test targeted SEND (create)
    # ============================================
    if "test send" in text:
        targeted_message = MessageActivityInput(
            text="🔒 [SEND] Targeted message - only YOU can see this!"
        ).with_recipient(ctx.activity.from_, is_targeted=True)

        result = await ctx.send(targeted_message)
        print(f"Targeted SEND result: {result}")
        return

    # ============================================
    # Test targeted REPLY
    # ============================================
    if "test reply" in text:
        targeted_reply = MessageActivityInput(text="🔒 [REPLY] Targeted reply - only YOU can see this!").with_recipient(
            ctx.activity.from_, is_targeted=True
        )

        result = await ctx.reply(targeted_reply)
        print(f"Targeted REPLY result: {result}")
        return

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
                # For updates, we just set is_targeted but don't change the recipient
                # The backend doesn't allow changing the recipient of a targeted message
                updated_message = MessageActivityInput(
                    text="🔒 [UPDATE] ✅ UPDATED targeted message! (only you see this)"
                )
                updated_message.id = result.id
                updated_message.is_targeted = True  # Mark as targeted for the API URL

                await ctx.send(updated_message)
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
    # Help / Default
    # ============================================
    if "help" in text:
        await ctx.reply(
            "**Targeted Messages Test Bot**\n\n"
            "**Commands:**\n"
            "- `test send` - Send a targeted message\n"
            "- `test reply` - Reply with a targeted message\n"
            "- `test update` - Send then update a targeted message\n"
            "- `test delete` - Send then delete a targeted message\n\n"
            "💡 *Test in a group chat to verify others don't see targeted messages!*"
        )
        return

    # Default
    await ctx.reply('Say "help" for available commands.')


if __name__ == "__main__":
    asyncio.run(app.start())
