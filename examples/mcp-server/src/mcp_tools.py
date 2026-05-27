"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
import uuid

from app import app
from mcp.server.fastmcp import FastMCP
from microsoft_teams.api import Account, CreateConversationParams
from microsoft_teams.cards import AdaptiveCard, ExecuteAction, SubmitData, TextBlock, TextInput
from models import (
    ApprovalRequestResult,
    ApprovalResult,
    AskResult,
    FindUserResult,
    NotifyResult,
    PendingAsk,
    ReplyResult,
    UserMatch,
)
from msgraph.generated.users.users_request_builder import UsersRequestBuilder  # type: ignore[import-untyped]
from state import approval_waiters, approvals, pending_asks, personal_conversations, reply_waiters

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
async def find_user(query: str) -> FindUserResult:
    """Find users in this tenant by partial name, email, or UPN.

    Returns up to 5 matches with their AAD object ids — pass an id to
    notify, ask, or request_approval.

    Requires the bot app registration to have User.ReadBasic.All
    (Application permission) with admin consent.
    """
    graph = app.get_app_graph()
    params = UsersRequestBuilder.UsersRequestBuilderGetQueryParameters(
        search=f'"displayName:{query}" OR "userPrincipalName:{query}"',
        select=["id", "displayName", "userPrincipalName"],
        top=5,
    )
    config = UsersRequestBuilder.UsersRequestBuilderGetRequestConfiguration(  # type: ignore[call-arg]
        query_parameters=params,
    )
    config.headers.add("ConsistencyLevel", "eventual")
    result = await graph.users.get(request_configuration=config)  # type: ignore[arg-type]
    matches = [
        UserMatch(
            id=u.id,
            display_name=u.display_name,
            user_principal_name=u.user_principal_name,
        )
        for u in ((result.value if result else None) or [])
        if u.id
    ]
    return FindUserResult(matches=matches)


@mcp.tool()
async def notify(user_id: str, message: str) -> NotifyResult:
    """Send a notification to a Teams user. No response expected."""
    conversation_id = await _get_or_create_conversation(user_id)
    await app.send(conversation_id=conversation_id, activity=message)
    return NotifyResult(notified=True, user_id=user_id)


@mcp.tool()
async def ask(user_id: str, question: str) -> AskResult:
    """Ask a Teams user a question. Returns a request_id — call wait_for_reply with it to get the answer."""
    conversation_id = await _get_or_create_conversation(user_id)
    request_id = str(uuid.uuid4())
    # Record the pending ask before sending so a fast reply is never lost.
    pending_asks[request_id] = PendingAsk(user_id=user_id)
    card = AdaptiveCard(
        body=[
            TextBlock(text=question, weight="Bolder", size="Medium", wrap=True),
            TextInput(
                id="reply",
                placeholder="Type your reply...",
                is_multiline=True,
                is_required=True,
                error_message="Please enter a reply.",
            ),
        ],
        actions=[
            ExecuteAction(title="Send")
            .with_data(SubmitData("ask_reply", {"request_id": request_id}))
            .with_associated_inputs("auto"),
        ],
    )
    try:
        await app.send(conversation_id=conversation_id, activity=card)
    except Exception:
        pending_asks.pop(request_id, None)
        raise
    return AskResult(request_id=request_id)


@mcp.tool()
async def get_reply(request_id: str) -> ReplyResult:
    """Snapshot the current reply state for an ask. Returns status 'pending' until the user responds."""
    entry = pending_asks.get(request_id)
    if not entry:
        raise ValueError(f"No ask found with request_id {request_id}.")
    return ReplyResult(status=entry.status, reply=entry.reply)


@mcp.tool()
async def wait_for_reply(request_id: str, timeout_seconds: int = 30) -> ReplyResult:
    """Wait for the user's reply to an earlier ask. Blocks up to timeout_seconds (default 30).

    Returns the reply when it arrives, or status='pending' if the timeout fires.
    """
    entry = pending_asks.get(request_id)
    if not entry:
        raise ValueError(f"No ask found with request_id {request_id}.")
    if entry.status == "answered":
        return ReplyResult(status=entry.status, reply=entry.reply)

    loop = asyncio.get_event_loop()
    if request_id not in reply_waiters or reply_waiters[request_id].done():
        reply_waiters[request_id] = loop.create_future()

    try:
        result = await asyncio.wait_for(asyncio.shield(reply_waiters[request_id]), timeout=float(timeout_seconds))
        return ReplyResult(status=result.status, reply=result.reply)
    except asyncio.TimeoutError:
        current = pending_asks.get(request_id)
        return ReplyResult(
            status=current.status if current else "pending",
            reply=current.reply if current else None,
        )


@mcp.tool()
async def request_approval(user_id: str, title: str, description: str) -> ApprovalRequestResult:
    """Send an approval request to a Teams user. Returns an approval_id — call wait_for_approval for the decision."""
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
    approvals[approval_id] = "pending"
    try:
        await app.send(conversation_id=conversation_id, activity=card)
    except Exception:
        approvals.pop(approval_id, None)
        raise
    return ApprovalRequestResult(approval_id=approval_id)


@mcp.tool()
async def get_approval(approval_id: str) -> ApprovalResult:
    """Snapshot the current status of an approval request. Returns 'pending', 'approved', or 'rejected'."""
    status = approvals.get(approval_id)
    if status is None:
        raise ValueError(f"No approval found with approval_id {approval_id}.")
    return ApprovalResult(approval_id=approval_id, status=status)


@mcp.tool()
async def wait_for_approval(approval_id: str, timeout_seconds: int = 30) -> ApprovalResult:
    """Wait for an approval decision. Blocks up to timeout_seconds (default 30).

    Returns 'approved' or 'rejected' when the user clicks, or 'pending' if the timeout fires.
    """
    status = approvals.get(approval_id)
    if status is None:
        raise ValueError(f"No approval found with approval_id {approval_id}.")
    if status != "pending":
        return ApprovalResult(approval_id=approval_id, status=status)

    loop = asyncio.get_event_loop()
    if approval_id not in approval_waiters or approval_waiters[approval_id].done():
        approval_waiters[approval_id] = loop.create_future()

    try:
        result = await asyncio.wait_for(asyncio.shield(approval_waiters[approval_id]), timeout=float(timeout_seconds))
        return ApprovalResult(approval_id=approval_id, status=result)  # type: ignore[arg-type]
    except asyncio.TimeoutError:
        current_status = approvals.get(approval_id, "pending")
        return ApprovalResult(approval_id=approval_id, status=current_status)  # type: ignore[arg-type]
