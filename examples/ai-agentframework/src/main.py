"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import re
from os import getenv

from agent import agent, tool_logger
from agent_framework import AgentSession
from microsoft_teams.api import (
    CitationAppearance,
    MessageActivity,
    MessageActivityInput,
    MessageSubmitActionInvokeActivity,
)
from microsoft_teams.apps import ActivityContext, App

# LOG_LEVEL controls third-party noise (httpx, mcp, azure-identity). Defaults to WARNING.
logging.basicConfig(level=getenv("LOG_LEVEL", "WARNING").upper())
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# App is the Teams bot host for this example.
app = App()

# Per-conversation sessions preserve message history across turns.
_sessions: dict[str, AgentSession] = {}


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    conversation_id = ctx.activity.conversation.id
    if conversation_id not in _sessions:
        _sessions[conversation_id] = agent.create_session()

    tool_logger.citations = {}

    full_text = ""
    async for chunk in agent.run(ctx.activity.text, session=_sessions[conversation_id], stream=True):
        if chunk.text:
            ctx.stream.emit(chunk.text)
            full_text += chunk.text

    used_positions = {int(n) for n in re.findall(r"\[(\d+)\]", full_text)}
    citations_list = list(tool_logger.citations.values())

    # add_ai_generated() adds the "AI-generated" label; add_feedback() enables thumbs up/down.
    # Emit with no text so the streamed content isn't duplicated in the final activity.
    reply = MessageActivityInput().add_ai_generated().add_feedback()
    for i, annotation in enumerate(citations_list, 1):
        if i in used_positions:
            reply.add_citation(
                position=i,
                appearance=CitationAppearance(
                    name=annotation.get("title") or f"Source {i}",
                    abstract=annotation.get("snippet") or "No description available.",
                    url=annotation.get("url"),
                ),
            )
    ctx.stream.emit(reply)


@app.on_message_submit_feedback
async def handle_feedback(ctx: ActivityContext[MessageSubmitActionInvokeActivity]):
    reaction = ctx.activity.value.action_value.reaction
    feedback = ctx.activity.value.action_value.feedback
    logger.info("feedback: %s | %s", reaction, feedback)


if __name__ == "__main__":
    asyncio.run(app.start())
