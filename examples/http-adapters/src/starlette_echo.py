"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Starlette Echo Bot
# ==================
# Teams echo bot using a custom StarletteAdapter.
#
# This demonstrates the "managed" pattern — the SDK manages the server lifecycle
# via app.start(). The adapter creates its own Starlette app and uvicorn server.
#
# Run:
#     python src/starlette_echo.py

import asyncio
import re

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette_adapter import StarletteAdapter

# 1. Create adapter
adapter = StarletteAdapter()


# 2. Add custom routes directly on the Starlette instance
async def health(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy"})


adapter.app.add_route("/health", health)


# 3. Create the Teams app with the adapter
app = App(http_server_adapter=adapter)


# 4. Handle incoming messages — streaming demo
@app.on_message_pattern(re.compile(r"^stream\b", re.IGNORECASE))
async def handle_stream(ctx: ActivityContext[MessageActivity]):
    ctx.stream.update("Starting stream...")
    await asyncio.sleep(0.5)

    words = "Hello from the Starlette adapter! This message is being streamed word by word.".split()
    for word in words:
        await asyncio.sleep(0.3)
        ctx.stream.emit(word + " ")


# 5. Echo fallback
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"[Starlette] You said: '{ctx.activity.text}'")


if __name__ == "__main__":
    asyncio.run(app.start())
