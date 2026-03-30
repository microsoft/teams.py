"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import ActivityContext, App

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
        await ctx.reply("Thanks for your message! This reply auto-quotes it using reply().")
        return

    # ============================================
    # quote() — quote a previously sent message by ID
    # ============================================
    if "test quote" in text:
        sent = await ctx.send("The meeting has been moved to 3 PM tomorrow.")
        await ctx.quote(sent.id, "Just to confirm — does the new time work for everyone?")
        return

    # ============================================
    # add_quote() — builder with response
    # ============================================
    if "test add" in text:
        sent = await ctx.send("Please review the latest PR before end of day.")
        msg = MessageActivityInput().add_quote(sent.id, "Done! Left my comments on the PR.")
        await ctx.send(msg)
        return

    # ============================================
    # Multi-quote with mixed responses
    # ============================================
    if "test multi" in text:
        sent_a = await ctx.send("We need to update the API docs before launch.")
        sent_b = await ctx.send("The design mockups are ready for review.")
        sent_c = await ctx.send("CI pipeline is green on main.")
        msg = (
            MessageActivityInput()
            .add_quote(sent_a.id, "I can take the docs — will have a draft by Thursday.")
            .add_quote(sent_b.id, "Looks great, approved!")
            .add_quote(sent_c.id)
        )
        await ctx.send(msg)
        return

    # ============================================
    # add_quote() + add_text() — manual control
    # ============================================
    if "test manual" in text:
        sent = await ctx.send("Deployment to staging is complete.")
        msg = MessageActivityInput().add_quote(sent.id).add_text(" Verified — all smoke tests passing.")
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
            "- `test quote` - quote() quotes a previously sent message\n"
            "- `test add` - add_quote() builder with response\n"
            "- `test multi` - Multi-quote with mixed responses (one bare quote with no response)\n"
            "- `test manual` - add_quote() + add_text() manual control\n\n"
            "Quote any message to me to see the parsed metadata!"
        )
        return

    await ctx.reply('Say "help" for available commands.')


if __name__ == "__main__":
    asyncio.run(app.start())
