"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from pathlib import Path
from typing import Any

from microsoft.teams.apps import App, FunctionContext
from microsoft.teams.devtools import DevToolsPlugin

app = App(plugins=[DevToolsPlugin()])
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
