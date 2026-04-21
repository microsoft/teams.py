"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from random import random

from microsoft_teams.api import CardAction, CardActionType, MessageActivity, MessageActivityInput, SuggestedActions
from microsoft_teams.apps import ActivityContext, App

app = App()

# List of sample messages to emit
STREAM_MESSAGES = [
    "🚀 App installation detected! Starting stream...",
    "📊 Initializing data streams...",
    "✅ Connection established",
    "🔄 Processing background tasks...",
    "📈 System metrics looking good",
    "💡 Ready to assist you!",
    "🌟 All systems operational",
    "📋 Checking configurations...",
    "🔧 Optimizing performance...",
    "✨ Stream test complete!",
]


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Stream messages to the user on any message activity."""

    ctx.stream.update("Stream starting...")
    await asyncio.sleep(1)

    # Stream messages with delays using ctx.stream.emit
    for message in STREAM_MESSAGES:
        await asyncio.sleep(random())
        ctx.stream.emit(message)

    # Add suggested actions to the final message
    ctx.stream.emit(
        MessageActivityInput().with_suggested_actions(
            SuggestedActions(
                to=[ctx.activity.from_.id],
                actions=[
                    CardAction(type=CardActionType.IM_BACK, title="Run again", value="Run again"),
                    CardAction(type=CardActionType.IM_BACK, title="Show status", value="Show status"),
                    CardAction(type=CardActionType.IM_BACK, title="Help", value="Help"),
                ],
            )
        )
    )


if __name__ == "__main__":
    asyncio.run(app.start())
