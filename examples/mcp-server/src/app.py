"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from microsoft_teams.api import (
    AdaptiveCardActionCardResponse,
    AdaptiveCardActionMessageResponse,
    AdaptiveCardInvokeActivity,
    AdaptiveCardInvokeResponse,
    MessageActivity,
)
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.cards import AdaptiveCard, TextBlock
from state import approval_waiters, approvals, pending_asks, personal_conversations, reply_waiters

app = App()
logger = logging.getLogger(__name__)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Cache 1:1 conversation IDs so MCP tools can DM users later."""
    user_id = ctx.activity.from_.id
    conversation_id = ctx.activity.conversation.id

    if ctx.activity.conversation.conversation_type == "personal":
        personal_conversations[user_id] = conversation_id

    logger.info(
        f"Received message from user {user_id} in conversation {conversation_id}. "
        "Replies to asks now arrive via adaptive card actions."
    )
    await ctx.reply("Hi! I'll let you know if I need anything.")


@app.on_card_action_execute("ask_reply")
async def handle_ask_reply(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Capture the user's typed reply from the ask adaptive card."""
    data = ctx.activity.value.action.data
    request_id = data.get("request_id")
    reply = data.get("reply") or ""

    if request_id and request_id in pending_asks and pending_asks[request_id].status == "pending":
        pending_asks[request_id].reply = reply
        pending_asks[request_id].status = "answered"
        # Signal any wait_for_reply callers.
        waiter = reply_waiters.get(request_id)
        if waiter and not waiter.done():
            waiter.set_result(pending_asks[request_id])
        return AdaptiveCardActionCardResponse(
            value=AdaptiveCard(
                version="1.4",
                body=[
                    TextBlock(text="Reply recorded", weight="Bolder", color="Good"),
                    TextBlock(text=reply, wrap=True),
                ],
            )
        )

    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Unable to record reply. The ask may be invalid or expired.",
    )


@app.on_card_action_execute("approval_response")
async def handle_approval_response(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Capture approve/reject decisions from approval cards."""
    data = ctx.activity.value.action.data
    approval_id = data.get("approval_id")
    decision = data.get("decision")
    if approval_id and approval_id in approvals and decision in ("approved", "rejected"):
        approvals[approval_id] = decision
        # Signal any wait_for_approval callers.
        waiter = approval_waiters.get(approval_id)
        if waiter and not waiter.done():
            waiter.set_result(decision)
        color = "Good" if decision == "approved" else "Attention"
        label = "Approved" if decision == "approved" else "Rejected"
        return AdaptiveCardActionCardResponse(
            value=AdaptiveCard(
                version="1.4",
                body=[TextBlock(text=label, weight="Bolder", color=color)],
            )
        )

    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Unable to record response. The approval request may be invalid or expired.",
    )
