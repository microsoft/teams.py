"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os

from microsoft.teams.api import MessageActivity
from microsoft.teams.app import ActivityContext, App

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

    if ctx.activity.text.lower().find("reply"):
        await ctx.reply("Hello! How can I assist you today?")
    else:
        await ctx.send(f"You said '{ctx.activity.text}'")


async def main():
    port = int(os.getenv("PORT", "3978"))
    await app.start(port=port)


if __name__ == "__main__":
    asyncio.run(main())
