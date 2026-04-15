"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import os
from typing import Annotated, Dict, cast

from mcp.server.fastmcp import FastMCP
from microsoft_teams.api import Account, CreateConversationParams, MessageActivityInput
from microsoft_teams.api.activities.message.message import MessageActivity
from microsoft_teams.apps import App
from microsoft_teams.apps.http import FastAPIAdapter
from microsoft_teams.apps.routing.activity_context import ActivityContext
from pydantic import BeforeValidator

# Maps user_id -> conversation_id.
# Populated on each incoming message and on first proactive send (via conversation create).
conversation_storage: Dict[str, str] = {}

# Maps activity_id -> conversation_id for user-sent messages.
# Needed by add_reaction/remove_reaction to locate the conversation from an activity_id alone.
activity_storage: Dict[str, str] = {}

# Maps activity_id -> conversation_id for bot-sent messages.
# Needed by update_message/delete_message to locate the conversation from an activity_id alone.
bot_activity_storage: Dict[str, str] = {}

# MCP Inspector sends activity IDs as JSON integers
ActivityId = Annotated[str, BeforeValidator(str)]

logger = logging.getLogger(__name__)

mcp = FastMCP("test-mcp")


async def _get_or_create_conversation(user_id: str) -> str:
    """Return the stored conversation_id for user_id, or create a new 1:1 conversation.

    Creating a conversation requires only the user's Teams ID and the tenant ID — the bot
    does not need to have exchanged messages with the user beforehand.
    """
    if user_id not in conversation_storage:
        tenant_id = os.getenv("TENANT_ID")
        resource = await app.api.conversations.create(
            CreateConversationParams(members=[Account(id=user_id)], tenant_id=tenant_id)
        )
        conversation_storage[user_id] = resource.id
    return conversation_storage[user_id]


@mcp.tool()
async def send_message(user_id: str, message: str) -> str:
    """Send a proactive message to a Teams user. Creates a conversation if one does not exist yet."""
    conversation_id = await _get_or_create_conversation(user_id)
    sent = await app.send(conversation_id=conversation_id, activity=message)
    # Store so update_message/delete_message can look up the conversation by activity_id.
    bot_activity_storage[sent.id] = conversation_id
    logger.info(f"[send_message] user_id={user_id} activity_id={sent.id}")
    return f"Message sent to user {user_id} (activity_id={sent.id})"


@mcp.tool()
async def update_message(activity_id: ActivityId, message: str) -> str:
    """Update a bot-sent message by its activity_id."""
    conversation_id = bot_activity_storage.get(activity_id)
    if not conversation_id:
        raise ValueError(
            f"No bot message found with activity_id {activity_id}. "
            "Send a message first and use the returned activity_id."
        )

    await app.api.conversations.activities(conversation_id).update(
        activity_id, MessageActivityInput().with_text(message)
    )
    logger.info(f"[update_message] activity_id={activity_id}")
    return f"Message {activity_id} updated"


@mcp.tool()
async def delete_message(activity_id: ActivityId) -> str:
    """Delete a bot-sent message by its activity_id."""
    conversation_id = bot_activity_storage.get(activity_id)
    if not conversation_id:
        raise ValueError(
            f"No bot message found with activity_id {activity_id}. "
            "Send a message first and use the returned activity_id."
        )

    await app.api.conversations.activities(conversation_id).delete(activity_id)
    # Remove from storage so stale activity_ids can't be reused.
    bot_activity_storage.pop(activity_id, None)
    logger.info(f"[delete_message] activity_id={activity_id}")
    return f"Message {activity_id} deleted"


@mcp.tool()
async def add_reaction(activity_id: ActivityId, reaction: str) -> str:
    """Add a reaction to a user message by its activity_id.
    Valid reactions: like, heart, 1f440_eyes, 2705_whiteheavycheckmark, launch, 1f4cc_pushpin"""
    # only react to messages the bot has received,
    # so this will fail if the user has never messaged the bot.
    conversation_id = activity_storage.get(activity_id)
    if not conversation_id:
        raise ValueError(f"No user message found with activity_id {activity_id}. The user must message the bot first.")

    await app.api.reactions.add(conversation_id, activity_id, reaction)
    return f"Reaction '{reaction}' added to {activity_id}"


@mcp.tool()
async def remove_reaction(activity_id: ActivityId, reaction: str) -> str:
    """Remove a reaction from a user message by its activity_id.
    Valid reactions: like, heart, 1f440_eyes, 2705_whiteheavycheckmark, launch, 1f4cc_pushpin"""
    conversation_id = activity_storage.get(activity_id)
    if not conversation_id:
        raise ValueError(f"No user message found with activity_id {activity_id}. The user must message the bot first.")

    await app.api.reactions.delete(conversation_id, activity_id, reaction)
    return f"Reaction '{reaction}' removed from {activity_id}"


@mcp.tool()
async def get_members(conversation_id: str) -> str:
    """Get all members of a conversation by its conversation_id"""
    members = await app.api.conversations.members(conversation_id).get_all()
    if not members:
        return "No members found"

    lines = [f"- {m.name} (id: {m.id})" for m in members]
    return "\n".join(lines)


app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle incoming messages and store context for MCP tools."""
    user_id = ctx.activity.from_.id
    conversation_id = ctx.activity.conversation.id

    # Keep both mappings up to date so all tools can look up by their natural key.
    conversation_storage[user_id] = conversation_id
    activity_storage[ctx.activity.id] = conversation_id

    logger.info(f"[handle_message] user_id={user_id} conversation_id={conversation_id} activity_id={ctx.activity.id}")
    await ctx.reply(f"You said: {ctx.activity.text}")


async def main() -> None:
    # app.initialize() must be called before mounting the MCP app so that
    # /api/messages is registered first — FastAPI routes take priority over
    # mounted sub-applications, and the MCP mount uses a catch-all path (/).
    await app.initialize()

    mcp_http_app = mcp.streamable_http_app()
    adapter = cast(FastAPIAdapter, app.server.adapter)
    # Register the MCP lifespan so its startup/shutdown hooks run with the server.
    adapter.lifespans.append(mcp_http_app.router.lifespan_context)
    adapter.app.mount("/", mcp_http_app)

    await app.start()


if __name__ == "__main__":
    asyncio.run(main())
