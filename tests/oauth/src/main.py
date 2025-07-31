"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft.teams.api import MessageActivity
from microsoft.teams.app import ActivityContext, App, SignInEvent
from microsoft.teams.app.events.types import ErrorEvent
from microsoft.teams.graph import enable_graph_integration

app = App()

# Enable Graph integration
enable_graph_integration()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

    user_text = ctx.activity.text.lower() if ctx.activity.text else ""

    if "graph" in user_text and ctx.is_signed_in:
        # Test Graph functionality
        await ctx.send("Testing Graph integration...")
        try:
            graph_client = getattr(ctx, "graph", None)
            if graph_client is not None:
                await ctx.send("Graph client available! Testing user info...")
                await graph_client.get_me()
                await ctx.send("Graph test successful! User info retrieved.")
            else:
                await ctx.send("Graph client not available - user may not be signed in properly.")
        except Exception as e:
            await ctx.send(f"Graph test failed: {str(e)}")
    elif "teams" in user_text and ctx.is_signed_in:
        # Test Teams Graph functionality
        await ctx.send("Testing Teams Graph integration...")
        try:
            graph_client = getattr(ctx, "graph", None)
            if graph_client is not None:
                await graph_client.get_my_teams()
                await ctx.send("Teams Graph test successful! Teams info retrieved.")
            else:
                await ctx.send("Graph client not available for Teams query.")
        except Exception as e:
            await ctx.send(f"Teams Graph test failed: {str(e)}")
    elif ctx.is_signed_in:
        await ctx.send(
            "You are signed in! Try typing 'graph' or 'teams' to test Graph functionality, or I'll sign you out."
        )
        await ctx.sign_out()
    else:
        ctx.logger.info("User requested sign-in.")
        await ctx.sign_in()


@app.event("sign_in")
async def handle_sign_in(event: SignInEvent):
    """Handle sign-in events."""
    await event.activity_ctx.send(
        "You are now signed in! 🎉\n\n"
        "Try these Graph tests:\n"
        "- Type 'graph' to test user info retrieval\n"
        "- Type 'teams' to test Teams data retrieval\n"
        "- Type anything else to sign out"
    )


@app.event("error")
async def handle_error(event: ErrorEvent):
    """Handle error events."""
    print(f"Error occurred: {event.error}")
    if event.context:
        print(f"Context: {event.context}")


if __name__ == "__main__":
    asyncio.run(app.start())
