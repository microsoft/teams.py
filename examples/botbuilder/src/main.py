"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import datetime
import sys
import traceback

from botbuilder.core import TurnContext
from botbuilder.integration.aiohttp import (
    CloudAdapter,
    ConfigurationBotFrameworkAuthentication,
)
from botbuilder.schema import Activity, ActivityTypes
from bots.echo_bot import EchoBot
from config import DefaultConfig
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.botbuilder import BotBuilderPlugin
from microsoft.teams.devtools import DevToolsPlugin

config = DefaultConfig()
adapter = CloudAdapter(ConfigurationBotFrameworkAuthentication(config))


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    print(f"\n [on_turn_error] unhandled error: {error}", file=sys.stderr)
    traceback.print_exc()

    # Send a message to the user
    await context.send_activity("The bot encountered an error or bug.")
    # Send a trace activity if we're talking to the Bot Framework Emulator
    if context.activity.channel_id == "emulator":
        trace_activity = Activity(
            label="TurnError",
            name="on_turn_error Trace",
            timestamp=datetime.datetime.now(),
            type=ActivityTypes.trace,
            value=f"{error}",
            value_type="https://www.botframework.com/schemas/error",
        )
        await context.send_activity(trace_activity)


adapter.on_turn_error = on_error

# Provide the Bot Framework's adapter and activity handler to `BotBuilderPlugin`
# BotBuilderPlugin will route incoming Teams messages through the adapter
# and invoke the handler to process and respond to each activity.
app = App(
    plugins=[
        BotBuilderPlugin(
            adapter=adapter,
            # This is the Bot Framework handler
            handler=EchoBot(),
        ),
        DevToolsPlugin(),
    ]
)


# This is the Teams SDK handler
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"TeamsSDK: You said {ctx.activity.text}")


if __name__ == "__main__":
    asyncio.run(app.start())
