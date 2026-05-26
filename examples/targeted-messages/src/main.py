"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from datetime import datetime, timezone

from microsoft_teams.api import MessageActivity, MessageActivityInput
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
    activity = ctx.activity
    text = (activity.text or "").lower()
    is_targeted_inbound = activity.recipient.is_targeted is True

    print(
        "[MESSAGE] Received:",
        {"text": text, "is_targeted": is_targeted_inbound, "from": activity.from_.id},
    )

    if "send public" in text:
        print("[send public]", {"is_targeted": is_targeted_inbound})
        if not is_targeted_inbound:
            await ctx.send("Send it to me privately first!")
        else:
            await ctx.send(
                MessageActivityInput(text="🌍 This is a public message — everyone can see this!").with_recipient(
                    activity.from_
                )
            )

    elif "send private" in text:
        print("[send private]", {"is_targeted": is_targeted_inbound})
        if not is_targeted_inbound:
            await ctx.send("Send it to me privately first!")
        else:
            # No explicit recipient needed: targeted inbound messages make ctx.send() default to targeted.
            await ctx.send("🔒 This is a private message — only YOU can see this!")

    elif "test update" in text:
        # UPDATE: Send a targeted message, then update it after 3 seconds
        conversation_id = activity.conversation.id

        targeted_message = MessageActivityInput(
            text="📝 This message will be **updated** in 3 seconds..."
        ).with_recipient(activity.from_, is_targeted=True)

        result = await ctx.send(targeted_message)

        if result.id:
            message_id = result.id

            async def update_after_delay():
                await asyncio.sleep(3)
                try:
                    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
                    updated_message = MessageActivityInput(
                        text=f"✏️ **Updated!** This message was modified at {timestamp}"
                    )
                    updated_message.id = message_id

                    await ctx.api.conversations.activities(conversation_id).update_targeted(message_id, updated_message)
                    print("[UPDATE] Updated targeted message")
                except Exception as err:
                    print(f"[UPDATE] Error: {err}")

            asyncio.create_task(update_after_delay())

        print("[UPDATE] Scheduled update in 3 seconds")

    elif "test delete" in text:
        # DELETE: Send a targeted message, then delete it after 3 seconds
        conversation_id = activity.conversation.id

        targeted_message = MessageActivityInput(
            text="🗑️ This message will be **deleted** in 3 seconds..."
        ).with_recipient(activity.from_, is_targeted=True)

        result = await ctx.send(targeted_message)

        if result.id:
            message_id = result.id

            async def delete_after_delay():
                await asyncio.sleep(3)
                try:
                    await ctx.api.conversations.activities(conversation_id).delete_targeted(message_id)
                    print("[DELETE] Deleted targeted message")
                except Exception as err:
                    print(f"[DELETE] Error: {err}")

            asyncio.create_task(delete_after_delay())

        print("[DELETE] Scheduled delete in 3 seconds")

    elif "test public" in text:
        # PUBLIC: Send a public message visible to everyone in the chat.
        await ctx.send(MessageActivityInput(text="📋 Here is the public result — everyone can see this!"))
        print("[PUBLIC] Sent public message")

    elif "test send" in text:
        # SEND: Send a targeted message visible only to the sender.
        targeted_message = MessageActivityInput(
            text="👋 This is a **targeted message** — only YOU can see this!"
        ).with_recipient(activity.from_, is_targeted=True)
        await ctx.send(targeted_message)
        print("[SEND] Sent targeted message")

    elif "test inbound" in text:
        # INBOUND: Detect whether the inbound message was itself targeted at the bot
        # (i.e. delivered as a slash command). Slash commands arrive as message
        # activities with `activity.recipient.is_targeted == True`.
        await ctx.send(
            "✅ Your message was delivered to me as a targeted message."
            if is_targeted_inbound
            else "ℹ️ Your message was delivered to me as a regular (broadcast) message."
        )
        print(f"[INBOUND] is_targeted={is_targeted_inbound}")

    elif "help" in text:
        await ctx.send(
            "**🎯 Targeted Messages Demo**\n\n"
            "**Commands:**\n"
            "- `test send` - Send a targeted message (only visible to you)\n"
            "- `test update` - Send a targeted message, then update it after 3 seconds\n"
            "- `test delete` - Send a targeted message, then delete it after 3 seconds\n"
            "- `test public` - Send a public reply (visible to all)\n"
            "- `send public` - Only send a public message if the incoming message is targeted\n"
            "- `send private` - Only send a private message if the incoming message is targeted\n"
            "- `test inbound` - Show whether the inbound message was targeted at the bot\n\n"
            "_Targeted messages are only visible to you, even in group chats!_"
        )

    else:
        await ctx.send(f"You said: '{activity.text}'\n\nType `help` to see available commands.")


if __name__ == "__main__":
    asyncio.run(app.start())
