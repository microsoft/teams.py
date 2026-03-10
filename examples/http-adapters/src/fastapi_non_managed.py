"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

Non-Managed FastAPI Server
==========================
Teams echo bot where YOU manage the server lifecycle.

This demonstrates the "non-managed" pattern — you create your own FastAPI app
with your own routes, wrap it in a FastAPIAdapter, call app.initialize() to
register the Teams routes, then start uvicorn yourself.

This is ideal when:
- You have an existing FastAPI app and want to add Teams bot support
- You need full control over server configuration (TLS, workers, middleware)
- You're deploying to a platform that manages the server (e.g. Azure Functions)

Run:
    python src/fastapi_non_managed.py
"""

import asyncio
import os

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App, FastAPIAdapter

# 1. Create your own FastAPI app with your own routes
my_fastapi = FastAPI(title="My App + Teams Bot")


@my_fastapi.get("/health")
async def health():
    return {"status": "healthy"}


@my_fastapi.get("/api/users")
async def users():
    return {"users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]}


@my_fastapi.get("/")
async def homepage():
    return HTMLResponse("""
        <h1>FastAPI + Teams Bot</h1>
        <p>Your FastAPI server is running with a Teams bot!</p>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/api/users">API: Users</a></li>
            <li><b>/api/messages</b> — Teams bot endpoint (added by SDK)</li>
        </ul>
    """)


# 2. Create a FastAPIAdapter wrapping your existing FastAPI app
adapter = FastAPIAdapter(app=my_fastapi)

# 3. Create the Teams app with the adapter
app = App(http_server_adapter=adapter)


# 4. Handle incoming messages
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"[FastAPI non-managed] You said: '{ctx.activity.text}'")


async def main():
    port = int(os.getenv("PORT", "3978"))

    # 5. Initialize only — registers /api/messages on our FastAPI app
    #    Does NOT start a server
    await app.initialize()

    print(f"Starting server on http://localhost:{port}")
    print("  GET  /              — Homepage")
    print("  GET  /health        — Health check")
    print("  GET  /api/users     — Users API")
    print("  POST /api/messages  — Teams bot endpoint (added by SDK)")

    # 6. Start your own uvicorn server
    config = uvicorn.Config(app=my_fastapi, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
