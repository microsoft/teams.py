"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging

from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.invoke.sign_in import SignInFailureInvokeActivity
from microsoft_teams.apps import ActivityContext, App, SignInEvent
from microsoft_teams.apps.events.types import ErrorEvent
from microsoft_teams.common import ConsoleFormatter

# Setup logging
logging.getLogger().setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(ConsoleFormatter())
logging.getLogger().addHandler(stream_handler)
logger = logging.getLogger(__name__)

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

    logger.info("User requested sign-in.")
    if ctx.is_signed_in:
        await ctx.send("You are already signed in. Logging you out.")
        await ctx.sign_out()
    else:
        await ctx.sign_in()


@app.event("sign_in")
async def handle_sign_in(event: SignInEvent):
    """Handle sign-in events."""
    await event.activity_ctx.send("You are now signed in!")


@app.on_signin_failure()
async def handle_signin_failure(ctx: ActivityContext[SignInFailureInvokeActivity]):
    """Handle sign-in failure events."""
    failure = ctx.activity.value
    print(f"Sign-in failed: {failure.code} - {failure.message}")
    await ctx.send("Sign-in failed.")


@app.event("error")
async def handle_error(event: ErrorEvent):
    """Handle error events."""
    print(f"Error occurred: {event.error}")
    if event.context:
        print(f"Context: {event.context}")


if __name__ == "__main__":
    asyncio.run(app.start())
