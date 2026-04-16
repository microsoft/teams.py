"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import os
import uuid

from app import app
from mcp.server.fastmcp import FastMCP
from microsoft_teams.api import Account, CreateConversationParams
from microsoft_teams.cards import AdaptiveCard, ExecuteAction, SubmitData, TextBlock
from models import ApprovalRequestResult, ApprovalResult, AskResult, NotifyResult, PendingAsk, ReplyResult
from state import approvals, pending_asks, personal_conversations, user_pending_ask

mcp = FastMCP("teams-bot")


async def _get_or_create_conversation(user_id: str) -> str:
    """Return the 1:1 conversation_id for user_id, creating one if needed."""
    if user_id in personal_conversations:
        return personal_conversations[user_id]
    tenant_id = os.getenv("TENANT_ID")
    resource = await app.api.conversations.create(
        CreateConversationParams(members=[Account(id=user_id)], tenant_id=tenant_id)
    )
    personal_conversations[user_id] = resource.id
    return resource.id


@mcp.tool()
async def notify(user_id: str, message: str) -> NotifyResult:
    """Send a notification to a Teams user. No response expected."""
    conversation_id = await _get_or_create_conversation(user_id)
    await app.send(conversation_id=conversation_id, activity=message)
    return NotifyResult(notified=True, user_id=user_id)


@mcp.tool()
async def ask(user_id: str, question: str) -> AskResult:
    """Ask a Teams user a question. Returns a request_id — use get_reply for their response."""
    conversation_id = await _get_or_create_conversation(user_id)
    request_id = str(uuid.uuid4())
    await app.send(conversation_id=conversation_id, activity=question)
    pending_asks[request_id] = PendingAsk(user_id=user_id)
    user_pending_ask[user_id] = request_id
    return AskResult(request_id=request_id)


@mcp.tool()
async def get_reply(request_id: str) -> ReplyResult:
    """Get the reply to a question sent with ask. Returns status 'pending' until the user responds."""
    entry = pending_asks.get(request_id)
    if not entry:
        raise ValueError(f"No ask found with request_id {request_id}.")
    return ReplyResult(status=entry.status, reply=entry.reply)


@mcp.tool()
async def request_approval(user_id: str, title: str, description: str) -> ApprovalRequestResult:
    """Send an approval request to a Teams user. Returns an approval_id — use get_approval for the decision."""
    conversation_id = await _get_or_create_conversation(user_id)
    approval_id = str(uuid.uuid4())
    card = AdaptiveCard(
        body=[
            TextBlock(text=title, weight="Bolder", size="Large", wrap=True),
            TextBlock(text=description, wrap=True),
        ],
        actions=[
            ExecuteAction(title="Approve").with_data(
                SubmitData("approval_response", {"approval_id": approval_id, "decision": "approved"})
            ),
            ExecuteAction(title="Reject").with_data(
                SubmitData("approval_response", {"approval_id": approval_id, "decision": "rejected"})
            ),
        ],
    )
    await app.send(conversation_id=conversation_id, activity=card)
    approvals[approval_id] = "pending"
    return ApprovalRequestResult(approval_id=approval_id)


@mcp.tool()
async def get_approval(approval_id: str) -> ApprovalResult:
    """Get the status of an approval request. Returns 'pending', 'approved', or 'rejected'."""
    status = approvals.get(approval_id)
    if status is None:
        raise ValueError(f"No approval found with approval_id {approval_id}.")
    return ApprovalResult(approval_id=approval_id, status=status)
