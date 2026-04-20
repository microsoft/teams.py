"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from typing import Any

from agent_framework import AgentSession
from host_agent import host_agent
from microsoft_teams.api import Attachment, MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App

logging.basicConfig(level=logging.WARNING)
for _log_name in ("__main__", "kb_agent", "host_agent"):
    logging.getLogger(_log_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = App()

_sessions: dict[str, AgentSession] = {}
_conversation_locks: dict[str, asyncio.Lock] = {}


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    query = ctx.activity.text or ""
    if not query:
        return

    logger.info("Message received: query=%r", query)

    conv_id = ctx.activity.conversation.id
    lock = _conversation_locks.setdefault(conv_id, asyncio.Lock())

    # Serialize messages within a conversation: a second message that arrives while the first is
    # still running would otherwise race on session history and leave orphaned function-call turns.
    async with lock:
        session = _sessions.setdefault(conv_id, AgentSession())
        session.state["cards"] = []
        session.state["teams_conversation_id"] = conv_id

        response = await host_agent.run(query, session=session)
        cards: list[dict[str, Any]] = session.state.get("cards", [])

        reply_text = response.messages[-1].text if response.messages else ""
        logger.info("Sending reply + %d adaptive card(s): reply=%r", len(cards), reply_text)
        await ctx.reply(reply_text)

        for card_dict in cards:
            await ctx.send(
                MessageActivityInput().add_attachments(
                    Attachment(content_type="application/vnd.microsoft.card.adaptive", content=card_dict)
                )
            )


if __name__ == "__main__":
    asyncio.run(app.start())
