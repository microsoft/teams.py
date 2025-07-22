"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

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

    @app.onMessage
    async def handle_message(ctx: ActivityContext[MessageActivity]):
        """Handle message activities using the new generated handler system."""
        print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
        print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

        await ctx.next()

    @app.event("activity")
    async def handle_activity_event(event):
        """Handle all activities using the new generated handler system."""
        activity = event.activity
        print(f"[GENERATED event('activity')] Activity event: {activity.type} (ID: {activity.id})")

    @app.onInvoke
    async def handle_invoke(ctx: ActivityContext[InvokeActivity]):
        """Handle invoke activities using the new generated handler system."""
        print(f"[GENERATED invoke handler] Invoke received: {ctx.activity.name}")

    @app.onActivity
    async def handle_activity(ctx: ActivityContext[Activity]):
        """Handle event activities using the new generated handler system."""
        print(f"[GENERATED onActivity] Event activity received: {ctx.activity.type}")
        await ctx.next()

    @app.onMessageExtSubmit
    async def handle_message_ext_submit(ctx: ActivityContext[MessageExtensionSubmitActionInvokeActivity]):
        """Handle message extension submit activities."""
        print(f"[GENERATED] Message extension submit received: {ctx.activity.text}")
        return {"status": "success"}

    @app.onMessageDelete
    async def handle_message_delete(ctx: ActivityContext[MessageDeleteActivity]):
        """Handle message deletion activities."""
        print(f"[GENERATED] Message deleted: {ctx.activity.id}")

    @app.onTyping
    async def handle_typing(ctx: ActivityContext[TypingActivity]):
        """Handle typing indicator activities."""
        print(f"[GENERATED] User is typing: {ctx.activity.from_}")
        return None  # Typing activities typically don't need responses

    @app.onEvent
    async def handle_event_activity(ctx: ActivityContext[EventActivity]):
        """Handle event activities (meetings, etc.)."""
        print(f"[GENERATED] Event received: {ctx.activity.name}")
        return {"status": "processed"}

    @app.event
    async def handle_activity_event_without_explicit_annotation(event: ActivityEvent):
        activity = event.activity
        print(f"[EVENT (no annotation)] Activity received: {activity.type} (ID: {activity.id})")

    @app.event
    async def handle_error(event: ErrorEvent):
        print(f"[EVENT] Error in {event.context.get('method', 'unknown')}: {event.error}")

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
