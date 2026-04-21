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
from local_tools import bind_app
from microsoft_teams.api import (
    AdaptiveCardAttachment,
    CardAction,
    CardActionType,
    CardTaskModuleTaskInfo,
    CitationAppearance,
    MessageActivity,
    MessageActivityInput,
    MessageFetchTaskInvokeActivity,
    MessageSubmitActionInvokeActivity,
    SuggestedActions,
    TaskModuleContinueResponse,
    TaskModuleInvokeResponse,
    card_attachment,
)
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.cards import AdaptiveCard, SubmitAction, TextBlock, TextInput

# LOG_LEVEL controls third-party noise. Defaults to WARNING.
logging.basicConfig(level=getenv("LOG_LEVEL", "WARNING").upper())
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# App is the Teams bot host for this example.
app = App()
bind_app(app)

# Per-conversation sessions preserve message history across turns.
_sessions: dict[str, AgentSession] = {}

_SUGGESTED_PROMPTS = [
    CardAction(type=CardActionType.IM_BACK, title="How do I stream in teams.py?", value="How do I stream in teams.py?"),
    CardAction(
        type=CardActionType.IM_BACK,
        title="How do I create an Adaptive Card in teams.py?",
        value="How do I create an Adaptive Card in teams.py?",
    ),
]


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    conversation_id = ctx.activity.conversation.id
    if conversation_id not in _sessions:
        _sessions[conversation_id] = agent.create_session()

    text = ctx.activity.text or ""
    tool_logger.citations = {}

    full_text = ""
    async for chunk in agent.run(text, session=_sessions[conversation_id], stream=True):
        if chunk.text:
            ctx.stream.emit(chunk.text)
            full_text += chunk.text

    reply = _build_reply(full_text, ctx)
    ctx.stream.emit(reply)


def _build_reply(full_text: str, ctx: ActivityContext[MessageActivity]) -> MessageActivityInput:
    # add_ai_generated() adds the "AI-generated" label; add_feedback() enables thumbs up/down.
    reply = MessageActivityInput().add_ai_generated().add_feedback(mode="custom")
    _attach_citations(reply, full_text)
    reply.with_suggested_actions(SuggestedActions(to=[ctx.activity.from_.id], actions=_SUGGESTED_PROMPTS))
    return reply


def _attach_citations(reply: MessageActivityInput, full_text: str) -> None:
    """Attach citations from tool_logger that were referenced in the reply text."""
    used_positions = {int(n) for n in re.findall(r"\[(\d+)\]", full_text)}
    for annotation in tool_logger.citations.values():
        pos = annotation["position"]
        if pos in used_positions:
            reply.add_citation(
                position=pos,
                appearance=CitationAppearance(
                    name=annotation.get("title") or f"Source {pos}",
                    abstract=annotation.get("snippet") or "No description available.",
                    url=annotation.get("url"),
                ),
            )


@app.on_message_fetch_task
async def handle_feedback_fetch_task(
    ctx: ActivityContext[MessageFetchTaskInvokeActivity],
) -> TaskModuleInvokeResponse:
    reaction = ctx.activity.value.data.action_value.reaction
    card = (
        AdaptiveCard(version="1.4")
        .with_body(
            [
                TextBlock(text=f"You clicked {reaction}. Tell us more:"),
                TextInput(id="feedbackText", placeholder="Enter your feedback here...", is_multiline=True),
            ]
        )
        .with_actions([SubmitAction(title="Submit")])
    )
    return TaskModuleInvokeResponse(
        task=TaskModuleContinueResponse(
            value=CardTaskModuleTaskInfo(
                title="Feedback",
                card=card_attachment(AdaptiveCardAttachment(content=card)),
            )
        )
    )


@app.on_message_submit_feedback
async def handle_feedback(ctx: ActivityContext[MessageSubmitActionInvokeActivity]):
    reaction = ctx.activity.value.action_value.reaction
    feedback = ctx.activity.value.action_value.feedback
    logger.info("feedback: %s | %s", reaction, feedback)


if __name__ == "__main__":
    asyncio.run(app.start())
