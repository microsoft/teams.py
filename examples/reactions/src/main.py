"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Example: Message Reactions

A bot that demonstrates adding and removing reactions to messages in Microsoft Teams.
This example shows how to use the ReactionClient to programmatically add and remove
reactions (like, heart, laugh, etc.) on messages.
"""

import asyncio

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.devtools import DevToolsPlugin

app = App(plugins=[DevToolsPlugin()])

# Mapping of reaction names to their display names
REACTION_TYPES = {
    "like": "👍 Like",
    "heart": "❤️ Heart",
    "laugh": "😂 Laugh",
    "surprised": "😮 Surprised",
    "sad": "😢 Sad",
    "angry": "😠 Angry",
    "plusone": "➕ Plus one",
}


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

        # Validate reaction type
        if reaction_type not in REACTION_TYPES:
            await ctx.reply(
                f"❌ Unknown reaction type: `{reaction_type}`\n\n"
                f"**Supported types:**\n" + "\n".join([f"- `{k}` - {v}" for k, v in REACTION_TYPES.items()])
            )
            return

        try:
            # Add the reaction using the ReactionClient
            await ctx.api.reactions.add(
                conversation_id=conversation_id,
                activity_id=activity_id,
                reaction_type=reaction_type,
            )

            await ctx.reply(f"✅ Added {REACTION_TYPES[reaction_type]} reaction to your message!")
            print(f"[REACTION] Added '{reaction_type}' to activity {activity_id}")

        except Exception as err:
            await ctx.reply(f"❌ Failed to add reaction: {err}")
            print(f"[ERROR] Failed to add reaction: {err}")

        return

    # ============================================
    # Remove Reaction
    # ============================================
    if text.startswith("unreact "):
        reaction_type = text[8:].strip()

        # Validate reaction type
        if reaction_type not in REACTION_TYPES:
            await ctx.reply(
                f"❌ Unknown reaction type: `{reaction_type}`\n\n"
                f"**Supported types:**\n" + "\n".join([f"- `{k}` - {v}" for k, v in REACTION_TYPES.items()])
            )
            return

        try:
            # Remove the reaction using the ReactionClient
            await ctx.api.reactions.delete(
                conversation_id=conversation_id,
                activity_id=activity_id,
                reaction_type=reaction_type,
            )

            await ctx.reply(f"✅ Removed {REACTION_TYPES[reaction_type]} reaction from your message!")
            print(f"[REACTION] Removed '{reaction_type}' from activity {activity_id}")

        except Exception as err:
            await ctx.reply(f"❌ Failed to remove reaction: {err}")
            print(f"[ERROR] Failed to remove reaction: {err}")

        return

    # ============================================
    # Help / Default
    # ============================================
    if "help" in text:
        await ctx.reply(
            "**Message Reactions Bot**\n\n"
            "**Commands:**\n"
            "- `react <type>` - Add a reaction to your message\n"
            "- `unreact <type>` - Remove a reaction from your message\n\n"
            "**Supported reaction types:**\n"
            + "\n".join([f"- `{k}` - {v}" for k, v in REACTION_TYPES.items()])
            + "\n\n**Example:**\n"
            "- `react like` - Adds a 👍 to your message\n"
            "- `unreact like` - Removes the 👍 from your message"
        )
        return

    # Default
    await ctx.reply('Say "help" for available commands, or try "react like"!')


if __name__ == "__main__":
    asyncio.run(app.start())
