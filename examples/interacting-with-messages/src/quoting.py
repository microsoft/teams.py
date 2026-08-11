from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext


async def handle_quoted_message(ctx: ActivityContext[MessageActivity]) -> bool:
    """Report metadata when the inbound message contains a quote."""
    quotes = ctx.activity.get_quoted_messages()
    if not quotes:
        return False

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
    return True


async def handle_quote_reply(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Reply with an automatic quote when the command matches."""
    if text != "quote reply":
        return False
    await ctx.reply("Thanks for your message! This reply auto-quotes it using reply().")
    return True


async def handle_quote_message(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Quote a previously sent message by ID when the command matches."""
    if text != "quote message":
        return False
    sent = await ctx.send("The meeting has been moved to 3 PM tomorrow.")
    await ctx.quote(sent.id, "Just to confirm - does the new time work for everyone?")
    return True


async def handle_quote_add(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Compose a quote with a response when the command matches."""
    if text != "quote add":
        return False
    sent = await ctx.send("Please review the latest PR before end of day.")
    await ctx.send(MessageActivityInput().add_quote(sent.id, "Done! Left my comments on the PR."))
    return True


async def handle_quote_batch(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Compose multiple quotes when the command matches."""
    if text != "quote batch":
        return False
    sent_a = await ctx.send("We need to update the API docs before launch.")
    sent_b = await ctx.send("The design mockups are ready for review.")
    sent_c = await ctx.send("CI pipeline is green on main.")
    message = (
        MessageActivityInput()
        .add_quote(sent_a.id, "I can take the docs - will have a draft by Thursday.")
        .add_quote(sent_b.id, "Looks great, approved!")
        .add_quote(sent_c.id)
    )
    await ctx.send(message)
    return True


async def handle_quote_manual(ctx: ActivityContext[MessageActivity], text: str) -> bool:
    """Manually combine a quote and text when the command matches."""
    if text != "quote manual":
        return False
    sent = await ctx.send("Deployment to staging is complete.")
    await ctx.send(MessageActivityInput().add_quote(sent.id).add_text(" Verified - all smoke tests passing."))
    return True
