"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from os import getenv

import uvicorn
from a2a_client import A2APeerClient
from a2a_server import build_agent_card, make_a2a_app
from agent import BotAgent
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App, FastAPIAdapter
from types_ import Config, TurnIdentity

load_dotenv(find_dotenv(usecwd=True))
logging.basicConfig(level=getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = getenv(name)
    if not value:
        raise ValueError(f"Required environment variable {name!r} is not set.")
    return value


config = Config(
    name=_require_env("BOT_NAME"),
    description=_require_env("BOT_DESCRIPTION"),
    self_url=_require_env("BOT_SELF_URL"),
    peer_name=_require_env("PEER_NAME"),
    peer_url=_require_env("PEER_URL"),
)

fastapi_app = FastAPI()
app = App(
    http_server_adapter=FastAPIAdapter(app=fastapi_app),
    client_id=getenv("BOT_APP_ID"),
    client_secret=getenv("BOT_APP_PASSWORD"),
    tenant_id=getenv("TENANT_ID"),
)

a2a_client = A2APeerClient(config)
bot_agent = BotAgent(config=config, a2a_client=a2a_client)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    aad_object_id = ctx.activity.from_.aad_object_id
    tenant_id = ctx.activity.conversation.tenant_id
    service_url = ctx.activity.service_url

    if not aad_object_id or not tenant_id or not service_url:
        logger.warning(
            "Skipping turn: activity missing identity required for handoff "
            "(aadObjectId=%s, tenantId=%s, serviceUrl=%s).",
            bool(aad_object_id),
            bool(tenant_id),
            bool(service_url),
        )
        await ctx.reply(
            "I can't process this message — it's missing the identity context this sample needs for cross-bot handoff."
        )
        return

    identity = TurnIdentity(
        aad_object_id=aad_object_id,
        user_name=ctx.activity.from_.name or "User",
        tenant_id=tenant_id,
        service_url=service_url,
    )

    conv_id = ctx.activity.conversation.id
    text = (ctx.activity.text or "").strip()

    reply = await bot_agent.run(conv_id, identity, text)
    if reply:
        await ctx.reply(reply)


async def main() -> None:
    # Build this bot's own AgentCard — equivalent to AgentCardFactory.Build(config) in C#.
    agent_card = build_agent_card(config)

    # Mount A2A Starlette sub-app; /.well-known/agent-card.json is served by
    # the A2AStarletteApplication automatically.
    a2a_starlette = make_a2a_app(teams_app=app, agent=bot_agent, config=config, agent_card=agent_card)
    fastapi_app.mount("/a2a", a2a_starlette.build())

    await app.initialize()

    port = int(getenv("PORT", "3978"))
    server = uvicorn.Server(uvicorn.Config(fastapi_app, host="0.0.0.0", port=port, log_level="info"))

    logger.info("%s listening on http://localhost:%s", config.name, port)
    logger.info("  Teams endpoint:    POST /api/messages")
    logger.info("  A2A endpoint:      POST /a2a")
    logger.info("  A2A agent card:    GET  /.well-known/agent-card.json (via /a2a)")
    logger.info("  Peer:              %s @ %s", config.peer_name, config.peer_url)

    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
