"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

"""
Example: Quoted Replies

A bot that demonstrates quoted reply features in Microsoft Teams.
Tests reply(), quote_reply(), add_quoted_reply(), and get_quoted_messages().
"""

app = App()


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities."""
    await ctx.reply(TypingActivityInput())

    text = (ctx.activity.text or "").lower()

    # ============================================
    # Read inbound quoted replies
    # ============================================
    quotes = ctx.activity.get_quoted_messages()
    if quotes:
        quote = quotes[0].quoted_reply
        info_parts = [f"Quoted message ID: {quote.message_id}"]
        if quote.sender_name:
            info_parts.append(f"From: {quote.sender_name}")
        if quote.preview:
            info_parts.append(f'Preview: "{quote.preview}"')
        if quote.is_reply_deleted:
            info_parts.append("(deleted)")
        if quote.validated_message_reference:
            info_parts.append("(validated)")

        await ctx.send("You sent a message with a quoted reply:\n\n" + "\n".join(info_parts))

    # ============================================
    # reply() — auto-quotes the inbound message
    # ============================================
    if "test reply" in text:
        await ctx.reply("This reply auto-quotes your message using reply()")
        return

    # ============================================
    # quote_reply() — quote a previously sent message by ID
    # ============================================
    if "test quote" in text:
        sent = await ctx.send("This message will be quoted next...")
        await ctx.quote_reply(sent.id, "This quotes the message above using quote_reply()")
        return

    # ============================================
    # add_quoted_reply() — builder with response
    # ============================================
    if "test add" in text:
        sent = await ctx.send("This message will be quoted next...")
        msg = MessageActivityInput().add_quoted_reply(sent.id, "This uses add_quoted_reply() with a response")
        await ctx.send(msg)
        return

    # ============================================
    # Multi-quote interleaved
    # ============================================
    if "test multi" in text:
        sent_a = await ctx.send("Message A — will be quoted")
        sent_b = await ctx.send("Message B — will be quoted")
        msg = (
            MessageActivityInput()
            .add_quoted_reply(sent_a.id, "Response to A")
            .add_quoted_reply(sent_b.id, "Response to B")
        )
        await ctx.send(msg)
        return

    # ============================================
    # add_quoted_reply() + add_text() — manual control
    # ============================================
    if "test manual" in text:
        sent = await ctx.send("This message will be quoted next...")
        msg = MessageActivityInput().add_quoted_reply(sent.id).add_text(" Custom text after the quote placeholder")
        await ctx.send(msg)
        return

    # ============================================
    # Help / Default
    # ============================================
    if "help" in text:
        await ctx.reply(
            "**Quoted Replies Test Bot**\n\n"
            "**Commands:**\n"
            "- `test reply` - reply() auto-quotes your message\n"
            "- `test quote` - quote_reply() quotes a previously sent message\n"
            "- `test add` - add_quoted_reply() builder with response\n"
            "- `test multi` - Multi-quote interleaved (quotes two separate messages)\n"
            "- `test manual` - add_quoted_reply() + add_text() manual control\n\n"
            "Quote any message to me to see the parsed metadata!"
        )
        return

    await ctx.reply('Say "help" for available commands.')


if __name__ == "__main__":
    asyncio.run(app.start())
