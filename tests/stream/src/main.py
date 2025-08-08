"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from random import random

from microsoft.teams.api import MessageActivity
from microsoft.teams.app import ActivityContext, App

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

    # Stream messages with delays using ctx.stream.emit
    for message in STREAM_MESSAGES:
        # Add some randomness to timing
        await asyncio.sleep(random())

        ctx.stream.emit(message)


if __name__ == "__main__":
    asyncio.run(app.start())
