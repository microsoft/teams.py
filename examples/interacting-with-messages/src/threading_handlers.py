"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft_teams.api import AgenticIdentity, MessageActivity
from microsoft_teams.apps import ActivityContext, App, ReplyMode

_REPLY_COMMANDS: dict[str, tuple[ReplyMode | None, str]] = {
    "thread reply": (
        None,
        "This reply uses the default reply mode, `combined`. "
        "In a chat it starts a thread under your top-level message, or stays in your thread, and quotes your message.",
    ),
    "thread reply unquoted": (
        "thread",
        'This reply uses `reply_mode="thread"`. '
        "It is placed like `combined`, without the quote when it lands in a thread.",
    ),
}


async def handle_thread_reply(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Reply to the inbound message in a thread when one of the commands matches.

    `thread reply` uses the app's reply mode, `combined` by default:
    in a chat, a reply to a top-level message starts a thread under it, a reply inside a thread stays in that thread,
    and the inbound message is quoted.
    `thread reply unquoted` passes `reply_mode="thread"`:
    the same placement, without the quote when the reply lands in a thread.
    The `quote` mode is shown by the `quote reply` command.
    In a channel every reply goes in the thread of the inbound message, so the mode only decides the quote.
    The app-wide default is set with `App(reply_mode=...)`.
    """
    command = _REPLY_COMMANDS.get(text)
    if command is None:
        return False
    reply_mode, reply_text = command
    await ctx.reply(reply_text, reply_mode=reply_mode)
    return True


async def handle_thread_send(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Send reactively without quoting when the command matches.

    In a channel, the message is sent in the same thread.
    In a chat, it matches the level of the inbound message:
    in the thread when the inbound message is in one, otherwise at top level.
    In a chat, unlike `reply`, `send` never starts a new thread.
    """
    if text != "thread send":
        return False
    await ctx.send(
        "This is sent without quoting. In a channel it goes in the same thread. "
        "In a chat it matches the level of your message."
    )
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
        service_url=ctx.conversation_ref.service_url,
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
        service_url=ctx.conversation_ref.service_url,
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
    """The ids come from the payload.

    `chat.id` identifies the chat and `channel.id` the channel.
    `reply_chain.id` is the root of the reply chain (thread).
    A top-level post in a channel carries a `reply_chain.id` equal to its own id.
    A payload without `reply_chain.id` does not establish a root,
    so the sample does not infer one from the channel or the activity id.
    An id the payload does not carry is None.
    """
    channel_data = ctx.activity.channel_data
    chat_id = channel_data.chat.id if channel_data and channel_data.chat else None
    channel_id = channel_data.channel.id if channel_data and channel_data.channel else None
    reply_chain_id = channel_data.reply_chain.id if channel_data and channel_data.reply_chain else None
    return chat_id if chat_id is not None else channel_id, reply_chain_id
