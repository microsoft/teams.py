"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import AgenticIdentity, MessageActivity
from microsoft_teams.apps import ActivityContext, App


async def handle_thread_reply(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send a reactive, quoted reply at the level of the inbound message when the command matches.

    In a thread the reply stays in the thread, and on a top-level message the reply stays top-level.
    """
    if text != "thread reply":
        return False
    await ctx.reply("This is a quoted reply, matching the threading level of your message.")
    return True


async def handle_thread_send(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send reactively without quoting when the command matches.

    The message matches the threading level of the inbound message.
    """
    if text != "thread send":
        return False
    await ctx.send("This is sent without quoting, matching the threading level of your message.")
    return True


async def handle_proactive_thread(app: App, ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send a proactive reply in the reply chain (thread) of the inbound message when the command matches.

    The reply chain is taken from `channel_data.reply_chain.id`.
    """
    if text != "thread proactive":
        return False
    conversation_id, reply_chain_id = _thread_reference(ctx)
    if not conversation_id or not reply_chain_id:
        await ctx.send(_INSUFFICIENT_METADATA)
        return True
    await app.reply(
        conversation_id,
        reply_chain_id,
        "This is a proactive reply in a thread, using `app.reply()`.",
        agentic_identity=_agentic_identity(ctx),
    )
    return True


async def handle_top_level_thread(app: App, ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send a new top-level message to the chat or channel, outside any reply chain (thread).

    Runs when the command matches.
    """
    if text != "thread top-level":
        return False
    conversation_id, _ = _thread_reference(ctx)
    if not conversation_id:
        await ctx.send(_INSUFFICIENT_METADATA)
        return True
    await app.send(
        conversation_id,
        "This is a new top-level message, sent with `app.send()` to the id of the chat or channel.",
        agentic_identity=_agentic_identity(ctx),
    )
    return True


def _agentic_identity(ctx: ActivityContext[MessageActivity]) -> AgenticIdentity | None:
    """A proactive send runs without the inbound activity, so an agentic user must be named explicitly.

    Returns None when the inbound recipient is not an agentic user.
    """
    return ctx.activity.recipient.agentic_identity


_INSUFFICIENT_METADATA = (
    "Not enough thread metadata on this message for the sample to address a thread: it reads "
    "`channel_data.chat.id` or `channel_data.channel.id` for the conversation id and "
    "`channel_data.reply_chain.id` for the root."
)


def _thread_reference(ctx: ActivityContext[MessageActivity]) -> tuple[str | None, str | None]:
    """Read the ids from the payload.

    `chat.id` identifies the chat and `channel.id` the channel.
    `reply_chain.id` is the root of the reply chain.
    An id the payload does not carry is None.
    """
    channel_data = ctx.activity.channel_data
    chat_id = channel_data.chat.id if channel_data and channel_data.chat else None
    channel_id = channel_data.channel.id if channel_data and channel_data.channel else None
    reply_chain_id = channel_data.reply_chain.id if channel_data and channel_data.reply_chain else None
    return chat_id if chat_id is not None else channel_id, reply_chain_id
