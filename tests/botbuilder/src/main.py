"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from botbuilder.core import ActivityHandler, TurnContext  # pyright: ignore[reportMissingTypeStubs]
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.botbuilder import BotBuilderPlugin
from microsoft.teams.devtools import DevToolsPlugin


class MyActivityHandler(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        print("Message activity received.")
        await turn_context.send_activity("hi from botbuilder...")


handler = MyActivityHandler()

app = App(
    plugins=[
        BotBuilderPlugin(handler=handler),
        DevToolsPlugin(),
    ]
)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    print("Handling message in app...")
    await ctx.send("hi from teams...")


if __name__ == "__main__":
    asyncio.run(app.start())
