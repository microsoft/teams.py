"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from typing import Any

from agent_framework import AgentSession
from microsoft_teams.api import Attachment, MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App
from orchestrator import orchestrator
from teams_helpers import extract_file_attachments, inject_file_list

logging.basicConfig(level=logging.WARNING)
for _log_name in ("__main__", "data_analyst", "file_search", "orchestrator"):
    logging.getLogger(_log_name).setLevel(logging.INFO)

logger = logging.getLogger(__name__)

app = App()

_sessions: dict[str, AgentSession] = {}
_conversation_locks: dict[str, asyncio.Lock] = {}


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    files_metadata = extract_file_attachments(ctx)
    query = ctx.activity.text or ""
    if not query and not files_metadata:
        return

    logger.info("Message received: query=%r, files=%d", query, len(files_metadata))

    if files_metadata:
        query = inject_file_list(query, files_metadata)

    conv_id = ctx.activity.conversation.id
    lock = _conversation_locks.setdefault(conv_id, asyncio.Lock())

    # Serialize messages within a conversation: a second message that arrives while the first is
    # still running would otherwise race on session history and leave orphaned function-call turns.
    async with lock:
        session = _sessions.setdefault(conv_id, AgentSession())
        session.state["cards"] = []
        session.state["teams_conversation_id"] = conv_id

        response = await orchestrator.run(query, session=session)
        cards: list[dict[str, Any]] = session.state.get("cards", [])

        reply_text = (response.messages[-1].text if response.messages else "") or "Done."
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
