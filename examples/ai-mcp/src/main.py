"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import json
import logging
import re
from os import getenv
from typing import Any, cast

from agent import agent, client, tool_logger
from agent_framework import AgentSession, ChatResponse, Message
from local_tools import CLARIFICATION_INPUT_ID, CLARIFICATION_VERB, pending_cards
from microsoft_teams.api import (
    AdaptiveCardActionMessageResponse,
    AdaptiveCardAttachment,
    AdaptiveCardInvokeActivity,
    AdaptiveCardInvokeResponse,
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

logging.basicConfig(level=getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

# App is the Teams bot host for this example.
app = App()

# Per-conversation sessions preserve message history across turns.
_sessions: dict[str, AgentSession] = {}

_FOLLOW_UPS_PROMPT = (
    "Based on the conversation so far, suggest exactly 2 short follow-up questions the user might want to ask next. "
    'Respond with JSON: {"followUps": ["question 1", "question 2"]}. '
    "Keep each question under 60 characters."
)


async def _generate_follow_ups(last_user_text: str, last_ai_text: str) -> list[CardAction]:
    """Generate 2 dynamic follow-up suggestions with the selected provider."""
    try:
        response: ChatResponse[Any] = await client.get_response(
            [
                Message(
                    "user",
                    contents=[
                        f"{_FOLLOW_UPS_PROMPT}\n\n"
                        f"Last user message: {last_user_text}\n"
                        f"Last assistant response: {last_ai_text}"
                    ],
                )
            ],
            options={"max_tokens": 200},
        )
        content = response.text or "{}"
        match = re.search(r"\{[\s\S]*\}", content)
        data = cast("dict[str, Any]", json.loads(match.group(0) if match else "{}"))
        follow_ups = data.get("followUps", [])
        if not isinstance(follow_ups, list):
            return []
        return [
            CardAction(type=CardActionType.IM_BACK, title=question, value=question)
            for question in cast("list[Any]", follow_ups)[:2]
            if isinstance(question, str)
        ]
    except Exception as exc:
        logger.warning("follow-up generation failed: %s", exc)
        return []


async def _run_agent_and_reply(
    ctx: ActivityContext[MessageActivity],
    session: AgentSession,
    text: str,
) -> None:
    """Run the agent and emit the reply, handling clarification cards or normal flow."""
    tool_logger.citations = {}
    cards: list[AdaptiveCard] = []
    pending_cards.set(cards)

    full_text = ""
    async for chunk in agent.run(text, session=session, stream=True):
        if chunk.text:
            ctx.stream.emit(chunk.text)
            full_text += chunk.text

    if cards:
        # Clarification card — discard any streamed text, then emit card-only.
        ctx.stream.clear_text()
        reply = MessageActivityInput().add_ai_generated()
        for card in cards:
            reply.add_card(card)
        ctx.stream.emit(reply)
    else:
        follow_ups = await _generate_follow_ups(text, full_text)
        reply = _build_reply(full_text, follow_ups, ctx)
        ctx.stream.emit(reply)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    conversation_id = ctx.activity.conversation.id
    if conversation_id not in _sessions:
        _sessions[conversation_id] = agent.create_session()
    text = ctx.activity.text or ""
    await _run_agent_and_reply(ctx, _sessions[conversation_id], text)


@app.on_card_action_execute(CLARIFICATION_VERB)
async def handle_clarification(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle the user's choice from a clarification card."""
    data = ctx.activity.value.action.data or {}
    choice = data.get(CLARIFICATION_INPUT_ID, "")
    if not choice:
        logger.warning("Clarification submit had no clarificationChoice.")
        return AdaptiveCardActionMessageResponse(
            status_code=200,
            type="application/vnd.microsoft.activity.message",
            value="OK",
        )
    conversation_id = ctx.activity.conversation.id
    if conversation_id not in _sessions:
        _sessions[conversation_id] = agent.create_session()

    await _run_agent_and_reply(ctx, _sessions[conversation_id], choice)  # type: ignore[arg-type]

    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="OK",
    )


def _build_reply(
    full_text: str,
    follow_ups: list[CardAction],
    ctx: ActivityContext[MessageActivity],
) -> MessageActivityInput:
    reply = MessageActivityInput().add_ai_generated().add_feedback(mode="custom")
    _attach_citations(reply, full_text)
    if follow_ups:
        reply.with_suggested_actions(SuggestedActions(to=[ctx.activity.from_.id], actions=follow_ups))
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


async def main() -> None:
    async with agent:
        await app.start()


if __name__ == "__main__":
    asyncio.run(main())
