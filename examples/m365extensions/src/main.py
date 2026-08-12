"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import re
from os import environ, path

from aiohttp import ClientSession, web
from cards import help_card, task_form_card, task_launcher_card
from dotenv import load_dotenv
from microsoft_agents.activity import (
    ActivityTypes,
    Channels,
    load_configuration_from_env,
)
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.hosting.aiohttp import (
    CloudAdapter,
    jwt_authorization_middleware,
    start_agent_process,
)
from microsoft_agents.hosting.core import (
    AgentApplication,
    MemoryStorage,
    RouteRank,
    TurnContext,
    TurnState,
)
from microsoft_agents.hosting.core.app import ApplicationOptions
from microsoft_teams.api import (
    MessageActivity,
    MessageActivityInput,
    MessageReactionActivity,
    TaskFetchInvokeActivity,
    TaskModuleContinueResponse,
    TaskModuleInvokeResponse,
    TaskModuleMessageResponse,
    TaskSubmitInvokeActivity,
)
from microsoft_teams.api.clients.api_client import ApiClient
from microsoft_teams.api.models.account import Account
from microsoft_teams.api.models.attachment import AdaptiveCardAttachment, card_attachment
from microsoft_teams.api.models.task_module import CardTaskModuleTaskInfo
from microsoft_teams.apps import ActivityContext
from microsoft_teams.m365extensions import is_teams_channel, use_teams_sdk

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("m365extensions-sample")

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def _command(name: str) -> re.Pattern[str]:
    mention = r"(?:<at\b[^>]*>.*?</at>|@\S+)"
    return re.compile(
        rf"\s*(?:{mention}\s*)*{re.escape(name)}[ \t]*(?:\r?\n[\s\S]*)?$",
        re.IGNORECASE | re.DOTALL,
    )


# ═══════════════════════════════ Bootstrap ═══════════════════════════════

load_dotenv(path.join(path.dirname(path.dirname(__file__)), ".env"))
agents_sdk_config = load_configuration_from_env(dict(environ))

STORAGE = MemoryStorage()
CONNECTION_MANAGER = MsalConnectionManager(**agents_sdk_config)
ADAPTER = CloudAdapter(connection_manager=CONNECTION_MANAGER)

# Auth handlers are configured in .env, not here:
#   AGENTAPPLICATION__USERAUTHORIZATION__HANDLERS__<name>__SETTINGS__AZUREBOTOAUTHCONNECTIONNAME
AUTH_HANDLER_IDS = tuple(agents_sdk_config.get("AGENTAPPLICATION", {}).get("USERAUTHORIZATION", {}).get("HANDLERS", {}))

AGENT_SDK_APP = AgentApplication[TurnState](
    options=ApplicationOptions(storage=STORAGE, adapter=ADAPTER),
    connection_manager=CONNECTION_MANAGER,
    **agents_sdk_config,
)


def _bypass_rules(context: TurnContext) -> bool:
    activity = context.activity
    return activity.type == ActivityTypes.invoke and (activity.name or "").lower().startswith("signin/")


TEAMS_APP = use_teams_sdk(AGENT_SDK_APP, CONNECTION_MANAGER, _bypass_rules)


@AGENT_SDK_APP.error
async def _on_error(context: TurnContext, error: Exception):
    log.exception("Unhandled error: %s", error)
    await context.send_activity(f"⚠️ {type(error).__name__}: {error}")


# ═══════════════════════ Teams SDK routes (teams.py) ═══════════════════════


@TEAMS_APP.on_message_pattern(_command("help"))
async def _help(ctx: ActivityContext[MessageActivity]):
    await ctx.send(MessageActivityInput().add_card(help_card()))


@TEAMS_APP.on_message_pattern(_command("react"))
async def _react(ctx: ActivityContext[MessageActivity]):
    response = await ctx.send("React to this message! I'll add 👍 and remove it.")
    conv_id = ctx.activity.conversation.id
    try:
        await ctx.api.conversations.add_reaction(conv_id, response.id, "like")
        await asyncio.sleep(2)
        await ctx.api.conversations.delete_reaction(conv_id, response.id, "like")
    except Exception:
        log.exception("react: reactions API call failed")


@TEAMS_APP.on_message_pattern(_command("quote"))
async def _quote(ctx: ActivityContext[MessageActivity]):
    await ctx.reply("Quoting your message!")


@TEAMS_APP.on_message_pattern(_command("targeted"))
async def _targeted(ctx: ActivityContext[MessageActivity]):
    sender = ctx.activity.from_
    targeted_msg = MessageActivityInput(text="👁️ This message is only visible to you.").with_recipient(
        Account(id=sender.id, name=sender.name), is_targeted=True
    )
    await ctx.send(targeted_msg)


@TEAMS_APP.on_message_pattern(_command("task"))
async def _task(ctx: ActivityContext[MessageActivity]):
    """Send a card whose button opens a dialog (task/fetch → task/submit)."""
    await ctx.send(MessageActivityInput().add_card(task_launcher_card()))


@TEAMS_APP.on_dialog_open
async def _on_task_fetch(
    ctx: ActivityContext[TaskFetchInvokeActivity],
) -> TaskModuleInvokeResponse:
    return TaskModuleInvokeResponse(
        task=TaskModuleContinueResponse(
            value=CardTaskModuleTaskInfo(
                title="Sample Task Module",
                card=card_attachment(AdaptiveCardAttachment(content=task_form_card())),
            )
        )
    )


@TEAMS_APP.on_dialog_submit
async def _on_task_submit(
    ctx: ActivityContext[TaskSubmitInvokeActivity],
) -> TaskModuleInvokeResponse:
    data = ctx.activity.value.data
    await ctx.send(f"[Teams SDK] Task module submitted. Data: {data}")
    return TaskModuleInvokeResponse(task=TaskModuleMessageResponse(value="Done."))


@TEAMS_APP.on_message_reaction
async def _on_message_reaction(ctx: ActivityContext[MessageReactionActivity]):
    added = [r.type for r in ctx.activity.reactions_added or []]
    removed = [r.type for r in ctx.activity.reactions_removed or []]
    await ctx.send(f"[Teams SDK] Reactions: added={added} removed={removed}")


# ═════════════════════ Agents SDK routes (AgentApplication) ═════════════════════


@AGENT_SDK_APP.message(_command("help"))
async def _help_non_teams(context: TurnContext, _state: TurnState):
    await context.send_activity(
        "[Agent SDK] Commands: help, channel, whoami, mail, signout, agents sdk react, agents sdk proactive.\n"
    )


@AGENT_SDK_APP.message(_command("channel"))
async def _channel(context: TurnContext, _state: TurnState):
    via = (
        "Teams turn with no matching teams.py route → fell through"
        if is_teams_channel(context.activity)
        else "non-Teams channel → passed straight through"
    )
    await context.send_activity(f"[Agent SDK] channelId={context.activity.channel_id} ({via})")


@AGENT_SDK_APP.message(_command("agents sdk react"))
async def _agents_sdk_react(context: TurnContext, _state: TurnState):
    if not is_teams_channel(context.activity):
        await context.send_activity(
            f"[Agent SDK] 'agents sdk react' needs the Teams reactions API; "
            f"channelId={context.activity.channel_id} returns 404 for it."
        )
        return
    response = await context.send_activity("[Agent SDK] Adding then removing 👍 via teams.py API client…")
    conv_id = context.activity.conversation.id
    api = ApiClient(service_url=context.activity.service_url, options=TEAMS_APP.api.http)
    try:
        await api.conversations.add_reaction(conv_id, response.id, "like")
        await asyncio.sleep(2)
        await api.conversations.delete_reaction(conv_id, response.id, "like")
    except Exception:
        log.exception("agents sdk react: reactions API call failed")


@AGENT_SDK_APP.message(_command("agents sdk proactive"))
async def _agents_sdk_proactive(context: TurnContext, _state: TurnState):
    conv_id = context.activity.conversation.id
    api = ApiClient(service_url=context.activity.service_url, options=TEAMS_APP.api.http)
    bot = context.activity.recipient
    outgoing = MessageActivityInput().add_text("[Teams SDK] Proactive message triggered from an Agents SDK handler!")
    # Bypassing teams.py's ActivitySender means nothing populates from_, and Direct Line
    # rejects the send without it.
    outgoing.from_ = Account(id=bot.id, name=bot.name)
    await api.conversations.create_activity(conv_id, outgoing)


# ═══════════════════════════ Authentication ═══════════════════════════
# Both handlers use the same AAD app but different ABS connections, so each holds its own
# token — signing in for one does not satisfy the other.


async def _graph_get(context: TurnContext, handler: str, resource: str):
    """GET a Graph resource with the token cached for `handler`. None on failure."""
    token = await AGENT_SDK_APP.auth.get_token(context, handler)
    if not token or not token.token:
        await context.send_activity(f"[Agent SDK] No token for the '{handler}' handler.")
        return None

    headers = {"Authorization": f"Bearer {token.token}"}
    async with ClientSession() as session:
        async with session.get(f"{GRAPH_BASE_URL}{resource}", headers=headers) as resp:
            body = await resp.json()
            if resp.status != 200:
                detail = body.get("error", {}).get("message", body)
                await context.send_activity(f"[Agent SDK] Graph {resource} returned {resp.status}: {detail}")
                return None
            return body


@AGENT_SDK_APP.message(_command("whoami"), auth_handlers=["graphuser"])
async def _whoami(context: TurnContext, _state: TurnState):
    # Sign-in already completed by the time this runs, so get_token reads from cache.
    me = await _graph_get(context, "graphuser", "/me")
    if me:
        await context.send_activity(
            f"[Agent SDK] {me.get('displayName')} ({me.get('userPrincipalName')})\n"
            f"Handler 'graphuser' — scope User.Read."
        )


@AGENT_SDK_APP.message(_command("mail"), auth_handlers=["graphmail"])
async def _mail(context: TurnContext, _state: TurnState):
    data = await _graph_get(context, "graphmail", "/me/messages?$top=3&$select=subject,receivedDateTime")
    if data is None:
        return
    messages = data.get("value", [])
    if not messages:
        await context.send_activity("[Agent SDK] Mailbox is empty.")
        return
    lines = "\n".join(f"• {m.get('subject') or '(no subject)'}" for m in messages)
    await context.send_activity(
        f"[Agent SDK] Latest {len(messages)} message(s):\n{lines}\nHandler 'graphmail' — scopes User.Read + Mail.Read."
    )


@AGENT_SDK_APP.message(_command("signout"))
async def _signout(context: TurnContext, _state: TurnState):
    for handler in AUTH_HANDLER_IDS:
        await AGENT_SDK_APP.auth.sign_out(context, handler)
    await context.send_activity(f"[Agent SDK] Signed out of: {', '.join(AUTH_HANDLER_IDS)}.")


# Every OAuth card is rendered with the same fixed "Sign in" text, so these callbacks are
# the only way to tell which connection a prompt belonged to.
async def _on_sign_in_success(context: TurnContext, _state: TurnState, handler_id: str | None = None):
    await context.send_activity(f"[Agent SDK] Signed in via '{handler_id}'.")


async def _on_sign_in_failure(context: TurnContext, _state: TurnState, handler_id: str | None = None):
    await context.send_activity(f"[Agent SDK] Sign-in failed for '{handler_id}'.")


AGENT_SDK_APP.auth.on_sign_in_success(_on_sign_in_success)
AGENT_SDK_APP.auth.on_sign_in_failure(_on_sign_in_failure)


# Sign-in cannot complete on email: Azure Bot Service flattens cards into a static image,
# so the button is inert. A started flow would then swallow every later turn before
# routing, leaving the mailbox silent. These routes outrank the two above and decline, so
# no flow ever begins.
#
# signout is declined here too. Tokens are keyed by (channelId, userId, connectionName),
# and the email identity (an SMTP address) never holds one, so signing out would always
# report success for zero work — and could never reach a token held on Teams anyway.
NO_AUTH_CHANNELS = {Channels.email}


def _blocked_auth_selector(name: str):
    pattern = _command(name)

    def selector(context: TurnContext) -> bool:
        return (
            context.activity.type == ActivityTypes.message
            and context.activity.channel_id in NO_AUTH_CHANNELS
            and re.fullmatch(pattern, context.activity.text or "") is not None
        )

    return selector


async def _decline_auth(context: TurnContext, _state: TurnState):
    await context.send_activity(
        f"[Agent SDK] Sign-in isn't supported on {context.activity.channel_id} — the OAuth "
        "card renders as a static image here, so it can't be clicked. Tokens are scoped per "
        "channel, so there is nothing to sign in or out of on this one. "
        "Try whoami / mail on Teams or Web Chat."
    )


for _name in ("whoami", "mail", "signout"):
    AGENT_SDK_APP.add_route(_blocked_auth_selector(_name), _decline_auth, rank=RouteRank.FIRST)


# ═══════════════════════════ Fallthrough ═══════════════════════════


@AGENT_SDK_APP.activity("message", rank=RouteRank.LAST)
async def _echo(context: TurnContext, _state: TurnState):
    text = (context.activity.text or "").strip()
    first_line = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    if first_line != text:
        text = f"{first_line} […]"
    await context.send_activity(f"[Agent SDK] ({context.activity.channel_id}) You said: {text}")


# ═══════════════════════════ HTTP wiring ═══════════════════════════


async def _entry_point(req: web.Request) -> web.Response:
    response = await start_agent_process(req, req.app["agent_sdk_app"], req.app["adapter"])
    return response if response is not None else web.Response(status=201)


if __name__ == "__main__":
    APP = web.Application(middlewares=[jwt_authorization_middleware])
    APP.router.add_post("/api/messages", _entry_point)
    APP["agent_sdk_app"] = AGENT_SDK_APP
    APP["adapter"] = ADAPTER
    APP["agent_configuration"] = CONNECTION_MANAGER.get_default_connection_configuration()

    web.run_app(
        APP,
        host=environ.get("HOST", "localhost"),
        port=int(environ.get("PORT", "3978")),
    )
