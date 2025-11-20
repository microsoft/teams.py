"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import json
import re
from typing import Annotated

from agent_framework import (
    AgentThread,
    ChatAgent,
    ChatMessage,
    FunctionApprovalRequestContent,
    FunctionApprovalResponseContent,
    FunctionCallContent,
    ai_function,
)
from agent_framework.azure import AzureOpenAIChatClient
from microsoft.teams.api import AdaptiveCardInvokeActivity, MessageActivity
from microsoft.teams.api.models.adaptive_card import (
    AdaptiveCardActionErrorResponse,
    AdaptiveCardActionMessageResponse,
)
from microsoft.teams.api.models.error import HttpError, InnerHttpError
from microsoft.teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.cards import AdaptiveCard, ExecuteAction, TextBlock
from microsoft.teams.devtools import DevToolsPlugin
from pydantic import Field

app = App(plugins=[DevToolsPlugin()])

# Thread storage keyed by conversation ID
threads: dict[str, AgentThread] = {}


# Define approval-required functions
@ai_function(approval_mode="always_require")
async def send_email(
    to: Annotated[str, Field(description="Recipient email address")],
    subject: Annotated[str, Field(description="Email subject")],
    body: Annotated[str, Field(description="Email body")],
) -> str:
    """Send an email to a recipient."""
    await asyncio.sleep(0.5)  # Simulate sending
    return f"✅ Email sent to {to} with subject '{subject}'"


@ai_function(approval_mode="always_require")
async def book_meeting_room(
    room: Annotated[str, Field(description="Room name or number")],
    date: Annotated[str, Field(description="Date in YYYY-MM-DD format")],
    time: Annotated[str, Field(description="Time in HH:MM format")],
) -> str:
    """Book a meeting room."""
    await asyncio.sleep(0.5)
    return f"✅ Booked {room} for {date} at {time}"


@ai_function(approval_mode="always_require")
async def create_calendar_event(
    title: Annotated[str, Field(description="Event title")],
    date: Annotated[str, Field(description="Date in YYYY-MM-DD format")],
    time: Annotated[str, Field(description="Time in HH:MM format")],
) -> str:
    """Create a calendar event."""
    await asyncio.sleep(0.5)
    return f"✅ Created calendar event '{title}' on {date} at {time}"


# Create agent (singleton, reused across conversations)
agent = ChatAgent(
    chat_client=AzureOpenAIChatClient(),
    instructions="""
        You are a helpful assistant that can manage emails, calendar events, and meeting rooms.
        When asked to perform actions, use the available tools to help the user.
    """,
    tools=[send_email, book_meeting_room, create_calendar_event],
)


def create_approval_card(request: FunctionApprovalRequestContent) -> AdaptiveCard:
    """Create an adaptive card for function approval.

    Args:
        request: FunctionApprovalRequestContent from agent response

    Returns:
        AdaptiveCard with approval/rejection actions
    """
    arguments = request.function_call.parse_arguments()

    return AdaptiveCard(
        body=[
            TextBlock(text="🔐 Approval Required", weight="Bolder", size="Large"),
            TextBlock(text=f"**Function:** `{request.function_call.name}`"),
            TextBlock(text="**Parameters:**"),
            TextBlock(text=f"```json\n{json.dumps(arguments, indent=2)}\n```"),
        ],
        actions=[
            ExecuteAction(title="✅ Approve").with_data(
                {
                    "type": "approval",
                    "action": "approve",
                    "request_id": request.id,
                    "function_call": request.function_call.to_dict(),
                }
            ),
            ExecuteAction(title="❌ Reject").with_data(
                {
                    "type": "approval",
                    "action": "reject",
                    "request_id": request.id,
                    "function_call": request.function_call.to_dict(),
                }
            ),
        ],
    )


@app.on_message_pattern(re.compile("approval .*"))
async def handle_approval_message(ctx: ActivityContext[MessageActivity]):
    """Handle approval workflow messages.

    This handler:
    1. Runs the agent with the user's message
    2. Checks if any function requires approval
    3. Sends adaptive card(s) if approval is needed
    4. Otherwise, sends the agent's response directly
    """
    ctx.logger.info("Handling approval message")

    conversation_id = ctx.activity.conversation.id
    text = ctx.activity.text.removeprefix("approval ")

    # Get or create thread for this conversation
    if conversation_id not in threads:
        threads[conversation_id] = agent.get_new_thread()
    thread = threads[conversation_id]

    # Run agent
    result = await agent.run(text, thread=thread)

    # Check for approval requests
    if result.user_input_requests:
        # Send adaptive card for each approval request
        for request in result.user_input_requests:
            card = create_approval_card(request)
            await ctx.send(card)
    else:
        # No approval needed, send result directly
        await ctx.reply(result.text)


@app.on_card_action
async def handle_approval_card_action(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    """Handle approval card submissions.

    This handler:
    1. Extracts the approval decision (approve/reject)
    2. Reconstructs the FunctionApprovalResponseContent
    3. Resumes the agent with the approval response
    4. Sends the final result back to the user
    """
    data = ctx.activity.value.action.data

    # Check if this is an approval action
    if data.get("type") != "approval":
        # Not our action, skip
        return AdaptiveCardActionMessageResponse(
            status_code=200,
            type="application/vnd.microsoft.activity.message",
            value="Action processed",
        )

    conversation_id = ctx.activity.conversation.id
    thread = threads.get(conversation_id)

    if not thread:
        await ctx.send("❌ Session expired. Please start over.")
        return AdaptiveCardActionMessageResponse(
            status_code=200,
            type="application/vnd.microsoft.activity.message",
            value="Session expired",
        )

    # Parse approval decision
    approved = data.get("action") == "approve"
    request_id = data.get("request_id")
    function_call_data = data.get("function_call")

    # Validate data
    if not request_id or not function_call_data:
        await ctx.send("❌ Invalid approval data.")
        return AdaptiveCardActionErrorResponse(
            status_code=400,
            type="application/vnd.microsoft.error",
            value=HttpError(
                code="BadRequest",
                message="Invalid approval data",
                inner_http_error=InnerHttpError(
                    status_code=400,
                    body={"error": "Missing request_id or function_call data"},
                ),
            ),
        )

    # Reconstruct FunctionApprovalResponseContent
    approval_response = FunctionApprovalResponseContent(
        id=request_id,
        function_call=FunctionCallContent.from_dict(function_call_data),
        approved=approved,
    )

    # Resume agent with approval response
    result = await agent.run(ChatMessage(role="user", contents=[approval_response]), thread=thread)

    # Send final result
    await ctx.send(result.text)

    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value="Approval processed",
    )


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Default message handler."""
    ctx.logger.info("Handling general message")


if __name__ == "__main__":
    asyncio.run(app.start())
