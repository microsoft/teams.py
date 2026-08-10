"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# `state=True` enables the per-turn state layer using the app's storage.
#
# With no other storage configured the app falls back to in-memory
# `LocalStorage`, so state is scoped to a single process and lost on restart —
# the SDK logs a warning to that effect. For production, pass a durable store
# via `App(state=StateOptions(storage=...))`
#
# State is loaded before each turn and saved automatically after it, then
# sealed — reading or writing `ctx.state` after the handler returns raises
# `TurnStateSealedError`.
app = App(state=True)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    """Track a per-conversation message count and a per-user first-seen name."""
    assert ctx.state is not None

    # Conversation scope: shared by everyone in the chat/channel.
    count = ctx.state.conversation.get("message_count", 0) + 1
    ctx.state.conversation["message_count"] = count

    # User scope: per-sender. `user` is None only when the activity has no sender.
    greeting = ""
    if ctx.state.user is not None:
        if "name" not in ctx.state.user:
            ctx.state.user["name"] = ctx.activity.from_.name
            greeting = f"Nice to meet you, {ctx.activity.from_.name}! "
        else:
            greeting = f"Welcome back, {ctx.state.user['name']}! "

    await ctx.send(f"{greeting}This conversation has seen {count} message(s).")


if __name__ == "__main__":
    asyncio.run(app.start())
