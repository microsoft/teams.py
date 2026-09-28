"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging

from dotenv import find_dotenv, load_dotenv
from microsoft_teams.api import MessageActivity
from microsoft_teams.api.activities.typing import TypingActivityInput
from microsoft_teams.apps import (
    ActivityContext,
    App,
    SocketModeDisconnectedEvent,
    SocketModeOptions,
    SocketModeReadyEvent,
    SocketModeReconnectedEvent,
)

load_dotenv(find_dotenv(usecwd=True))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-7s %(name)s: %(message)s")
# Negotiate, handshake, readiness, and per-geo lifecycle all log under this namespace.
logging.getLogger("microsoft_teams.apps.socket_mode").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

app = App(
    socket_mode=SocketModeOptions(
        negotiate_base_url="https://canary.botapi.skype.com",
    )
)


# Handlers are transport-agnostic: the exact same code works over HTTP or Socket Mode.
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    await ctx.send(TypingActivityInput())
    await ctx.send(f'you said "{ctx.activity.text}"')


# `app.socket_mode` is the inbound transport; subscribe to its events to observe each
# geo's connection independently. These are purely observational — inbound delivery
# keeps working across reconnects without any handler changes.


def on_ready(event: SocketModeReadyEvent) -> None:
    logger.info("[socket] geo '%s' ready (connection_id=%s)", event.geo, event.frame.connection_id)

    # `app.start()` blocks until shutdown, so the per-geo snapshot is taken here rather
    # than after the call.
    if app.socket_mode:
        logger.info("[socket] aggregate status: %s", app.socket_mode.status)
        for geo, status in app.socket_mode.geo_statuses:
            logger.info("[socket]   %s: %s", geo, status)


def on_disconnected(event: SocketModeDisconnectedEvent) -> None:
    # Inbound delivery for this geo is paused while it reconnects; the other geos keep
    # serving. No action needed — the supervisor reconnects automatically.
    logger.warning("[socket] geo '%s' disconnected: %s; reconnecting...", event.geo, event.error)


def on_reconnected(event: SocketModeReconnectedEvent) -> None:
    logger.info("[socket] geo '%s' reconnected; inbound delivery resumed", event.geo)


if app.socket_mode:
    app.socket_mode.events.on("ready", on_ready)
    app.socket_mode.events.on("disconnected", on_disconnected)
    app.socket_mode.events.on("reconnected", on_reconnected)


if __name__ == "__main__":
    asyncio.run(app.start())
