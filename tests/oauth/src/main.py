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
            get_graph_client = getattr(ctx, "get_graph_client", None)
            if get_graph_client is not None:
                graph_client = await get_graph_client()
                if graph_client is not None:
                    await ctx.send("Graph client available! Testing user info...")
                    user_info = await graph_client.get_me()
                    print(f"User info retrieved: {user_info}")
                    # Handle user_info as a dict since Graph API returns dict-like objects
                    try:
                        if hasattr(user_info, "get"):
                            display_name = str(user_info.get("display_name", "N/A"))  # pyright: ignore[reportUnknownMemberType]
                        elif hasattr(user_info, "__dict__"):
                            display_name = str(getattr(user_info, "display_name", "N/A"))
                        else:
                            display_name = str(user_info)
                    except Exception:
                        display_name = "N/A"
                    await ctx.send(f"Graph test successful!  \nUser info retrieved.  \nDisplay Name: {display_name}")
                else:
                    await ctx.send("Graph client not available - user may not be signed in properly.")
            else:
                await ctx.send("Graph integration not enabled.")
        except Exception as e:
            await ctx.send(f"Graph test failed: {str(e)}")
    elif "teams" in user_text and ctx.is_signed_in:
        # Test Teams Graph functionality
        await ctx.send("Testing Teams Graph integration...")
        try:
            get_graph_client = getattr(ctx, "get_graph_client", None)
            if get_graph_client is not None:
                graph_client = await get_graph_client()
                if graph_client is not None:
                    # First check what scopes we have
                    await ctx.send("Checking token scopes...")
                    await graph_client.check_token_scopes()
                    # Then try to get teams
                    await ctx.send("Attempting to get teams...")
                    teams_info = await graph_client.get_my_teams()
                    # Handle teams_info as a dict since Graph API returns dict-like objects
                    try:
                        if hasattr(teams_info, "get"):
                            teams_list = teams_info.get("value", [])  # pyright: ignore[reportUnknownMemberType]
                            teams_count = len(teams_list) if teams_list else 0  # pyright: ignore[reportUnknownArgumentType]
                        elif hasattr(teams_info, "__dict__"):
                            teams_list = getattr(teams_info, "value", [])
                            teams_count = len(teams_list) if teams_list else 0
                        else:
                            teams_count = 0
                    except Exception:
                        teams_count = 0
                    await ctx.send(f"Teams Graph test successful!  \nFound {teams_count} teams.")
                else:
                    await ctx.send("Graph client not available for Teams query.")
            else:
                await ctx.send("Graph integration not enabled.")
        except Exception as e:
            await ctx.send(f"Teams Graph test failed: {str(e)}")
    elif "signout" in user_text and ctx.is_signed_in:
        # Sign out the user when they explicitly request it
        await ctx.send("Signing you out now...")
        await ctx.sign_out()
        await ctx.send("You have been signed out. Send any message to sign in again.")
    elif ctx.is_signed_in:
        await ctx.send(
            "You are signed in! Try typing 'graph' or 'teams' to test Graph functionality, or 'signout' to sign out."
        )
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
        "- Type 'signout' to sign out\n"
        "- Type anything else to see this menu"
    )


@app.event("error")
async def handle_error(event: ErrorEvent):
    """Handle error events."""
    print(f"Error occurred: {event.error}")
    if event.context:
        print(f"Context: {event.context}")


if __name__ == "__main__":
    asyncio.run(app.start())
