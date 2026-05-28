"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any

from microsoft_teams.apps import App, FunctionContext

# Surface SDK INFO/WARNING logs (including the anonymous-mode startup warning
# emitted when CLIENT_ID / CLIENT_SECRET / TENANT_ID are not configured).
logging.basicConfig(level=logging.INFO)

app = App()
app.tab("test", str(Path("Web/dist").resolve()))


@app.func
async def post_to_chat(ctx: FunctionContext[Any]):
    """
    Sends a message to the current conversation and returns the conversation ID.
    """
    await ctx.send(ctx.data["message"])
    return {"conversationId": ctx.conversation_id}


if __name__ == "__main__":
    asyncio.run(app.start())
