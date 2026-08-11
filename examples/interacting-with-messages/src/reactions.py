import asyncio
import logging

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App

logger = logging.getLogger(__name__)


async def handle_add_reaction(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Add a reaction to the inbound message when the command matches."""
    prefix = "reaction add "
    if not text.startswith(prefix):
        return False
    reaction_type = text.removeprefix(prefix).strip()
    if not reaction_type:
        return False

    await ctx.api.conversations.add_reaction(
        conversation_id=ctx.activity.conversation.id,
        activity_id=ctx.activity.id,
        reaction_type=reaction_type,
    )
    logger.info("[REACTION] Added '%s' to activity %s", reaction_type, ctx.activity.id)
    return True


async def handle_remove_reaction(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Add, then remove, a reaction from the inbound message when the command matches."""
    prefix = "reaction remove "
    if not text.startswith(prefix):
        return False
    reaction_type = text.removeprefix(prefix).strip()
    if not reaction_type:
        return False

    await ctx.api.conversations.add_reaction(
        conversation_id=ctx.activity.conversation.id,
        activity_id=ctx.activity.id,
        reaction_type=reaction_type,
    )
    await asyncio.sleep(2)
    await ctx.api.conversations.delete_reaction(
        conversation_id=ctx.activity.conversation.id,
        activity_id=ctx.activity.id,
        reaction_type=reaction_type,
    )
    logger.info("[REACTION] Cycled '%s' on activity %s", reaction_type, ctx.activity.id)
    return True


async def handle_proactive_reaction(app: App, ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send a bot message and react to it with app-level APIs when the command matches."""
    if text != "reaction proactive":
        return False

    sent = await app.send(
        ctx.conversation_ref.conversation.id,
        "This message was sent and reacted to using app-level APIs.",
    )
    await ctx.api.conversations.add_reaction(
        conversation_id=ctx.activity.conversation.id,
        activity_id=sent.id,
        reaction_type="like",
    )
    return True
