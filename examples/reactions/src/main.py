"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

"""
Example: Message Reactions

A bot that demonstrates adding and removing reactions to messages in Microsoft Teams.
This example shows how to use the ReactionClient to programmatically add and remove
reactions (like, heart, laugh, etc.) on messages.
"""

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities."""
    await ctx.reply(TypingActivityInput())

    text = (ctx.activity.text or "").lower().strip()
    conversation_id = ctx.activity.conversation.id
    activity_id = ctx.activity.id

    # ============================================
    # Add Reaction
    # ============================================
    if text.startswith("react "):
        reaction_type = text[6:].strip()

        await ctx.api.reactions.add(
            conversation_id=conversation_id,
            activity_id=activity_id,
            reaction_type=reaction_type,
        )

        await ctx.reply(f"✅ Added {reaction_type} reaction to your message!")
        print(f"[REACTION] Added '{reaction_type}' to activity {activity_id}")

    # ============================================
    # Remove Reaction
    # ============================================
    if text.startswith("unreact "):
        reaction_type = text[8:].strip()

        await ctx.api.reactions.delete(
            conversation_id=conversation_id,
            activity_id=activity_id,
            reaction_type=reaction_type,
        )

        await ctx.reply(f"✅ Removed {reaction_type} reaction from your message!")
        print(f"[REACTION] Removed '{reaction_type}' from activity {activity_id}")

    # ============================================
    # Help / Default
    # ============================================
    if "help" in text:
        await ctx.reply(
            "**Message Reactions Bot**\n\n"
            "**Commands:**\n"
            "- `react <type>` - Add a reaction to your message\n"
            "- `unreact <type>` - Remove a reaction from your message\n\n"
            "- `react like` - Adds a 👍 to your message\n"
            "- `unreact like` - Removes the 👍 from your message"
        )
        return

    # Default
    await ctx.reply('Say "help" for available commands, or try "react like"!')


if __name__ == "__main__":
    asyncio.run(app.start())
