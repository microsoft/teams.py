"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: reportUnusedFunction=false

import asyncio
import os

from dotenv import load_dotenv
from microsoft.teams.api import Activity, InvokeActivity, MessageActivity, MessageExtensionSubmitActionInvokeActivity
from microsoft.teams.api.activities import EventActivity, MessageDeleteActivity, TypingActivity
from microsoft.teams.app import App
from microsoft.teams.app.events import ActivityEvent, ErrorEvent, StartEvent, StopEvent
from microsoft.teams.app.routing.activity_context import ActivityContext

load_dotenv()


async def main() -> None:
    """Test the basic App framework."""
    print("Creating Teams App...")

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")
    tenant_id = os.getenv("TENANT_ID")
    port = int(os.getenv("PORT", "3978"))

    if not client_id or not client_secret:
        print("Error: CLIENT_ID and CLIENT_SECRET environment variables must be set")
        print("Please copy .env.example to .env and fill in your values")
        return

    print(f"Using CLIENT_ID: {client_id}")
    print(f"Using CLIENT_SECRET: {client_secret}")
    print(f"Using TENANT_ID: {tenant_id}")

    app = App()

    @app.on_message
    async def handle_message(ctx: ActivityContext[MessageActivity]):
        """Handle message activities using the new generated handler system."""
        print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
        print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

        # Test the new graph clients
        if ctx.user_graph:
            try:
                me = await ctx.user_graph.me.get()
                display_name = me.display_name if me and me.display_name else "Unknown"
                print(f"[GRAPH] User graph client available - User: {display_name}")
            except Exception as e:
                print(f"[GRAPH] Error using user graph: {e}")
        else:
            print(f"[GRAPH] User graph client not available (signed in: {ctx.is_signed_in})")

        if ctx.app_graph:
            try:
                # Try a simple app-only operation - this might require specific permissions
                print("[GRAPH] App graph client available")
            except Exception as e:
                print(f"[GRAPH] Error using app graph: {e}")
        else:
            print("[GRAPH] App graph client not available")

        await ctx.next()

    @app.event("activity")
    async def handle_activity_event(event: ActivityEvent) -> None:
        """Handle all activities using the new generated handler system."""
        activity = event.activity
        print(f"[GENERATED event('activity')] Activity event: {activity.type} (ID: {activity.id})")

    @app.on_invoke
    async def handle_invoke(ctx: ActivityContext[InvokeActivity]):
        """Handle invoke activities using the new generated handler system."""
        print(f"[GENERATED invoke handler] Invoke received: {ctx.activity.name}")

    @app.on_activity
    async def handle_activity(ctx: ActivityContext[Activity]):
        """Handle event activities using the new generated handler system."""
        print(f"[GENERATED onActivity] Event activity received: {ctx.activity.type}")
        await ctx.next()

    @app.on_message_ext_submit
    async def handle_message_ext_submit(
        ctx: ActivityContext[MessageExtensionSubmitActionInvokeActivity],
    ):
        """Handle message extension submit activities."""
        print("[GENERATED] Message extension submit received")
        # Return a proper messaging extension response
        from microsoft.teams.api.models import MessagingExtensionActionResponse

        return MessagingExtensionActionResponse(compose_extension=None)

    @app.on_message_delete
    async def handle_message_delete(ctx: ActivityContext[MessageDeleteActivity]):
        """Handle message deletion activities."""
        print(f"[GENERATED] Message deleted: {ctx.activity.id}")

    @app.on_typing
    async def handle_typing(ctx: ActivityContext[TypingActivity]):
        """Handle typing indicator activities."""
        print(f"[GENERATED] User is typing: {ctx.activity.from_}")
        return None  # Typing activities typically don't need responses

    @app.on_event
    async def handle_event_activity(ctx: ActivityContext[EventActivity]) -> None:
        """Handle event activities (meetings, etc.)."""
        print(f"[GENERATED] Event received: {ctx.activity.name}")
        # Event handlers should return None, not a dict

    @app.event
    async def handle_activity_event_without_explicit_annotation(event: ActivityEvent):
        activity = event.activity
        print(f"[EVENT (no annotation)] Activity received: {activity.type} (ID: {activity.id})")

    @app.event
    async def handle_error(event: ErrorEvent):
        """Handle error events."""
        context_info = "unknown"
        if event.context is not None:
            context_info = event.context.get("method", "unknown")
        print(f"[EVENT] Error in {context_info}: {event.error}")

    @app.event
    async def handle_start(event: StartEvent):
        print(f"[EVENT] App started successfully on port {event.port}")

    @app.event("stop")
    async def handle_stop(event: StopEvent):
        print(
            f"[EVENT] App stopped {event}",
        )

    print(f"Starting app on port {port}...")

    await app.start(port=port)


if __name__ == "__main__":
    asyncio.run(main())
