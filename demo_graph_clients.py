"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: reportUnusedFunction=false

import asyncio
import os

from dotenv import load_dotenv
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import App
from microsoft.teams.apps.routing.activity_context import ActivityContext

load_dotenv()


async def main() -> None:
    """Test the graph clients integration in the new Apps framework."""
    print("Creating Teams App with Graph Clients...")

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    tenant_id = os.getenv("TENANT_ID")
    port = int(os.getenv("PORT", "3979"))

    if not client_id or not client_secret:
        print("Error: CLIENT_ID and CLIENT_SECRET environment variables must be set")
        print("Please copy .env.example to .env and fill in your values")
        return

    print(f"Using CLIENT_ID: {client_id}")
    print(f"Using TENANT_ID: {tenant_id}")

    app = App()

    @app.on_message
    async def handle_message(ctx: ActivityContext[MessageActivity]):
        """Handle message activities and demonstrate graph clients."""
        print(f"[MESSAGE] Received: {ctx.activity.text}")
        print(f"[MESSAGE] From: {ctx.activity.from_}")

        # Test the graph clients integration
        if ctx.user_graph:
            try:
                me = await ctx.user_graph.me.get()
                display_name = me.display_name if me and me.display_name else "Unknown"
                print(f"[GRAPH] ✅ User graph client available - User: {display_name}")
                await ctx.send(f"Hello {display_name}! Graph client is working.")
            except Exception as e:
                print(f"[GRAPH] ❌ Error using user graph: {e}")
                await ctx.send("User graph client is available but encountered an error.")
        else:
            print(f"[GRAPH] ⚠️ User graph client not available (signed in: {ctx.is_signed_in})")
            await ctx.send("User graph client not available. Please sign in first.")

        if ctx.app_graph:
            try:
                print("[GRAPH] ✅ App graph client is available")
                await ctx.send("App graph client is configured and ready for app-only operations.")
            except Exception as e:
                print(f"[GRAPH] ❌ Error with app graph: {e}")
        else:
            print("[GRAPH] ⚠️ App graph client not available")

    print(f"Starting app on port {port}...")
    await app.start(port=port)


if __name__ == "__main__":
    asyncio.run(main())
