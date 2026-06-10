"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import datetime
import logging
import traceback

from botbuilder.core import TurnContext
from botbuilder.integration.aiohttp import (
    CloudAdapter,
    ConfigurationBotFrameworkAuthentication,
)
from botbuilder.schema import Activity, ActivityTypes
from bots.echo_bot import EchoBot
from config import DefaultConfig
from microsoft_teams.api import AdaptiveCardInvokeActivity, MessageActivity
from microsoft_teams.api.models.adaptive_card import AdaptiveCardActionMessageResponse
from microsoft_teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.botbuilder import BotBuilderAdapter
from microsoft_teams.cards import ActionSet, AdaptiveCard, ExecuteAction, SubmitData, TextBlock

# Surface SDK INFO/WARNING logs (including the anonymous-mode startup warning
# emitted when CLIENT_ID / CLIENT_SECRET / TENANT_ID are not configured).
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

config = DefaultConfig()
adapter = CloudAdapter(ConfigurationBotFrameworkAuthentication(config))


# Catch-all for errors.
async def on_error(context: TurnContext, error: Exception):
    logger.error(f"[on_turn_error] unhandled error: {error}")
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


def botbuilder_card() -> AdaptiveCard:
    return AdaptiveCard(
        body=[
            TextBlock(text="Handled by BotBuilder", weight="Bolder", wrap=True),
            TextBlock(text="This Action.Execute invoke is handled before the Teams SDK route.", wrap=True),
            ActionSet(
                actions=[ExecuteAction(title="Run BotBuilder action").with_data(SubmitData("botbuilder_action"))]
            ),
        ],
    )


def teams_app_card() -> AdaptiveCard:
    return AdaptiveCard(
        body=[
            TextBlock(text="Handled by Teams App", weight="Bolder", wrap=True),
            TextBlock(text="This Action.Execute invoke falls through to the Teams SDK app route.", wrap=True),
            ActionSet(actions=[ExecuteAction(title="Run Teams action").with_data(SubmitData("teams_action"))]),
        ],
    )


# Provide the Bot Framework's adapter and activity handler to `BotBuilderAdapter`.
# The adapter runs BotBuilder at the HTTP boundary before forwarding to Teams SDK routes.
app = App(
    http_server_adapter=BotBuilderAdapter(
        cloud_adapter=adapter,
        # This is the Bot Framework handler
        handler=EchoBot(),
    ),
)


# This is the Teams SDK handler
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"TeamsSDK: You said {ctx.activity.text}")
    await ctx.send(botbuilder_card())
    await ctx.send(teams_app_card())


@app.on_card_action_execute("teams_action")
async def handle_teams_action(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    await ctx.send("Teams SDK handled the card action.")
    return AdaptiveCardActionMessageResponse(value="Action processed successfully")


if __name__ == "__main__":
    asyncio.run(app.start())
