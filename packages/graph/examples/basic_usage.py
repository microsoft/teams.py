"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Basic usage example for Teams Graph integration.

This example demonstrates how to use the Graph integration in a Teams bot.
"""

from microsoft.teams.api import MessageActivity
from microsoft.teams.app import App
from microsoft.teams.app.routing import ActivityContext
from microsoft.teams.graph import enable_graph_integration

# Create Teams app
app = App()

# Enable Graph integration - this adds the 'graph' property to all contexts
enable_graph_integration()


@app.on_message
async def handle_message(context: ActivityContext[MessageActivity]):
    """Handle incoming messages with Graph integration."""

    # Check if user is signed in
    if not context.is_signed_in:
        await context.sign_in()
        return

    try:
        # Zero-configuration Graph access!
        # This line demonstrates the magic - no setup required
        me = await context.graph.me.get()

        # Send greeting with user's display name from Graph
        await context.reply(f"Hello {me.display_name}! 👋")

        # Get user's joined teams
        teams_response = await context.graph.users.by_user_id("me").joined_teams.get()
        teams = teams_response.value

        if teams:
            team_names = [team.display_name for team in teams[:5]]  # First 5 teams
            team_list = "\n• ".join(team_names)
            await context.send(f"Your teams:\n• {team_list}")

            if len(teams) > 5:
                await context.send(f"... and {len(teams) - 5} more teams")
        else:
            await context.send("You're not a member of any teams.")

    except Exception as e:
        context.logger.error(f"Graph API error: {e}")
        await context.reply("Sorry, I couldn't access your Microsoft Graph data.")


@app.on_message
async def handle_team_info(context: ActivityContext[MessageActivity]):
    """Example of accessing team information."""

    if not context.is_signed_in:
        await context.sign_in()
        return

    # This is just an example - in a real bot you'd parse the message
    # to extract team ID or use the current Teams context
    if "team info" in context.activity.text.lower():
        try:
            # Get all teams first
            teams_response = await context.graph.users.by_user_id("me").joined_teams.get()

            if teams_response.value:
                first_team = teams_response.value[0]

                # Get detailed team information
                team_details = await context.graph.teams.by_team_id(first_team.id).get()

                info = f"""
**{team_details.display_name}**
• Description: {team_details.description or "No description"}
• Created: {team_details.created_date_time.strftime("%Y-%m-%d") if team_details.created_date_time else "Unknown"}
• Visibility: {team_details.visibility or "Unknown"}
"""
                await context.send(info)
            else:
                await context.send("You're not a member of any teams.")

        except Exception as e:
            context.logger.error(f"Team info error: {e}")
            await context.reply("Sorry, I couldn't get team information.")


if __name__ == "__main__":
    """Run the bot locally for testing."""
    import asyncio

    print("Starting Teams Graph integration example bot...")
    print("Make sure you have:")
    print("1. Valid Teams app credentials configured")
    print("2. Microsoft Graph permissions granted")
    print("3. User signed in to the bot")

    # Run the app
    asyncio.run(app.start())
