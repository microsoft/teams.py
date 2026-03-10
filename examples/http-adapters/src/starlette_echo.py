"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Starlette Echo Bot
==================
Teams echo bot using a custom StarletteAdapter.

This demonstrates the "managed" pattern — the SDK manages the server lifecycle
via app.start(). The adapter creates its own Starlette app and uvicorn server.

Run:
    python src/starlette_echo.py
"""

import asyncio

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App
from starlette_adapter import StarletteAdapter

# 1. Create adapter
adapter = StarletteAdapter()


# 2. Add custom routes directly on the Starlette instance
@adapter.app.route("/health")
async def health(request):
    from starlette.responses import JSONResponse

    return JSONResponse({"status": "healthy"})


# 3. Create the Teams app with the adapter
app = App(http_server_adapter=adapter)


# 4. Handle incoming messages
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"[Starlette] You said: '{ctx.activity.text}'")


if __name__ == "__main__":
    asyncio.run(app.start())
