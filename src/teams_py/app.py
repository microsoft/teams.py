"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os

from dotenv import load_dotenv
from microsoft.teams.app import App, AppOptions
from microsoft.teams.app.events import ActivityEvent, ErrorEvent, StartEvent, StopEvent

load_dotenv()


async def my_activity_handler(activity: dict) -> dict:
    """Custom activity handler for testing."""
    activity_type = activity.get("type", "unknown")
    activity_id = activity.get("id", "unknown")

    print(f"[CUSTOM HANDLER] Processing activity {activity_id} of type {activity_type}")

    await asyncio.sleep(2)

    print(f"[CUSTOM HANDLER] Finished processing activity {activity_id}")

    return {
        "status": "success",
        "message": f"Custom handler processed {activity_type}",
        "timestamp": "2024-01-01T00:00:00Z",
    }


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

    app = App(
        AppOptions(
            activity_handler=my_activity_handler,
        )
    )

    @app.event
    async def handle_activity(event: ActivityEvent):
        activity = event.activity
        print(f"[EVENT] Activity received: {activity.get('type')} (ID: {activity.get('id')})")

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
