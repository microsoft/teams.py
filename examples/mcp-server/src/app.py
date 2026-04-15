"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging

from microsoft_teams.api.activities.invoke.adaptive_card.action import AdaptiveCardInvokeActivity
from microsoft_teams.api.activities.message.message import MessageActivity
from microsoft_teams.api.models.adaptive_card.adaptive_card_action_response import AdaptiveCardActionMessageResponse
from microsoft_teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft_teams.apps.app import App
from microsoft_teams.apps.routing.activity_context import ActivityContext
from state import approvals, pending_asks, personal_conversations, user_pending_ask

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Capture user replies and cache 1:1 conversation IDs."""
    user_id = ctx.activity.from_.id
    conversation_id = ctx.activity.conversation.id

    if ctx.activity.conversation.conversation_type == "personal":
        personal_conversations[user_id] = conversation_id

    request_id = user_pending_ask.pop(user_id, None)
    if request_id and request_id in pending_asks:
        pending_asks[request_id].reply = ctx.activity.text or ""
        pending_asks[request_id].status = "answered"
        await ctx.reply("Got it, thank you!")
    else:
        logging.info(
            f"Received message from user {user_id} in conversation {conversation_id}, but no pending ask found."
        )
        await ctx.reply("Hi! I'll let you know if I need anything.")


@app.on_card_action_execute("approval_response")
async def handle_approval_response(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Capture approve/reject decisions from approval cards."""
    data = ctx.activity.value.action.data
    approval_id = data.get("approval_id")
    decision = data.get("decision")
    if approval_id and approval_id in approvals and decision in ("approved", "rejected"):
        approvals[approval_id] = decision
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Response recorded",
    )
