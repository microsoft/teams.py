"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from app import app
from mcp_tools import mcp
from microsoft_teams.apps.http.fastapi_adapter import FastAPIAdapter
from typing_extensions import cast


async def main() -> None:
    # app.initialize() must be called before mounting the MCP app so that
    # /api/messages is registered first — FastAPI routes take priority over
    # mounted sub-applications, and the MCP mount uses a catch-all path (/).
    await app.initialize()

    mcp_http_app = mcp.streamable_http_app()
    adapter = cast(FastAPIAdapter, app.server.adapter)
    # Register the MCP lifespan so its startup/shutdown hooks run with the server.
    adapter.lifespans.append(mcp_http_app.router.lifespan_context)
    adapter.app.mount("/", mcp_http_app)

    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
