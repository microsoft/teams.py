"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging

from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App, SignInEvent
from microsoft_teams.apps.events.types import ErrorEvent, SignInFailureEvent
from microsoft_teams.common import ConsoleFormatter
from microsoft_teams.graph import get_graph_client

# Setup logging
logging.getLogger().setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(ConsoleFormatter())
logging.getLogger().addHandler(stream_handler)
logger = logging.getLogger(__name__)

# Pending sign-in hints are stored in per-turn state, which lets connection-less
# callbacks be routed back to the flow that started them.
app = App(state=True)

# Multi-connection OAuth: two named connections registered with add_oauth_flow, each
# driven through the OAuthFlow it returns.
#
# Bot needs two OAuth connections configured in Azure, named "profile" and
# "mail", matching the names passed below. Grant "User.Read" to the first and
# "Mail.Read" to the second.
profile = app.add_oauth_flow("profile", oauth_card_text="Sign in to read your profile")
mail = app.add_oauth_flow("mail", oauth_card_text="Sign in to read your mail")


@profile.on_signin
async def on_profile_signin(event: SignInEvent) -> None:
    """Only fires for the `profile` connection, using that connection's token."""
    client = get_graph_client(event.token_response.token)
    me = await client.me.get()
    name = me.display_name if me else "unknown"
    await event.activity_ctx.send(f"Signed in as **{name}**.")


@mail.on_signin
async def on_mail_signin(event: SignInEvent) -> None:
    """Only fires for the `mail` connection — a token the profile flow does not have."""
    client = get_graph_client(event.token_response.token)
    page = await client.me.messages.get()
    subjects = [m.subject or "(no subject)" for m in (page.value or [])[:3]] if page else []
    body = "\n".join(f"- {s}" for s in subjects) if subjects else "_no messages_"
    await event.activity_ctx.send(f"Latest mail:\n{body}")


@profile.on_signin_failure
async def on_profile_failure(event: SignInFailureEvent) -> None:
    await event.activity_ctx.send(f"Profile sign-in failed: {event.code} - {event.message}")


@mail.on_signin_failure
async def on_mail_failure(event: SignInFailureEvent) -> None:
    await event.activity_ctx.send(f"Mail sign-in failed: {event.code} - {event.message}")


@app.event("sign_in")
async def on_any_signin(event: SignInEvent) -> None:
    """Fires for every connection. `connection_name` says which one completed."""
    logger.info("sign-in completed on connection %r", event.connection_name)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    # The bot is @mentioned in group chats and channels, so drop the mention
    # before dispatching to keep the same commands working in every scope.
    text = (ctx.activity.strip_mentions_text().text or "").strip().lower()

    if text == "sign in profile":
        # Returns the token directly when one is already cached, otherwise sends a
        # card and returns None; the flow's on_signin handler fires once it completes.
        if await profile.sign_in(ctx):
            await ctx.send("Already signed in for profile access.")
        return

    if text == "sign in mail":
        if await mail.sign_in(ctx):
            await ctx.send("Already signed in for mail access.")
        return

    if text == "sign out":
        await profile.sign_out(ctx)
        await mail.sign_out(ctx)
        await ctx.send("Signed out of both connections.")
        return

    if text == "status":
        # Tokens are tracked per connection, so these can differ.
        lines: list[str] = []
        for flow in (profile, mail):
            state = "signed in" if await flow.is_signed_in(ctx) else "signed out"
            lines.append(f"- `{flow.connection_name}`: {state}")
        await ctx.send("\n".join(lines))
        return

    await ctx.send("Try `sign in profile`, `sign in mail`, `status`, or `sign out`.")


@app.event("error")
async def handle_error(event: ErrorEvent) -> None:
    logger.error("error: %s (context=%s)", event.error, event.context)


if __name__ == "__main__":
    asyncio.run(app.start())
