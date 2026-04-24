"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from os import getenv

import uvicorn
from a2a_client import send_a2a
from a2a_server import make_a2a_app
from agent import BotAgent, current_user_conv_id
from cards import ASK_REPLY_ACTION
from dotenv import load_dotenv
from messages import ReplyMessage
from microsoft_teams.api import AdaptiveCardInvokeActivity, MessageActivity
from microsoft_teams.api.models.adaptive_card import AdaptiveCardActionMessageResponse
from microsoft_teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.common import ConsoleFormatter
from state import BotState

# Bot B (Bob) — symmetric with Bot A. See bot_a.py for the flow description.
load_dotenv()

NAME = "Bob"
TEAMS_PORT = int(getenv("BOT_B_PORT", "3979"))
A2A_HOST = getenv("BOT_B_A2A_HOST", "localhost")
A2A_PORT = int(getenv("BOT_B_A2A_PORT", "5001"))
SELF_A2A_URL = f"http://{A2A_HOST}:{A2A_PORT}/"
ALICE_URL = getenv("ALICE_A2A_URL", "http://localhost:5000/")
ALLOWED_PEER_URLS = [ALICE_URL]

logging.getLogger().setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(ConsoleFormatter())
logging.getLogger().addHandler(_handler)
logger = logging.getLogger(__name__)

app = App(
    client_id=getenv("BOT_B_CLIENT_ID"), client_secret=getenv("BOT_B_CLIENT_SECRET"), tenant_id=getenv("TENANT_ID")
)
state = BotState(name=NAME)
bot_agent = BotAgent(self_name=NAME, self_a2a_url=SELF_A2A_URL, peers={"alice": ALICE_URL}, state=state)

# Description goes into Bob's A2A AgentCard. Peers' LLMs read it to
# decide whether to forward a question. Tweak to match your scenario.
DESCRIPTION = "Bob — a Teams bot whose human operator answers backend and infrastructure questions."


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    text = (ctx.activity.text or "").strip()
    conv_id = ctx.activity.conversation.id
    # Only 1:1 conversations become the operator channel for inbound asks.
    if ctx.activity.conversation.conversation_type == "personal":
        state.operator_conv_id = conv_id

    agent = await bot_agent.get_agent()
    session = bot_agent.session_for(conv_id)
    current_user_conv_id.set(conv_id)
    async for chunk in agent.run(text, session=session, stream=True):
        if chunk.text:
            ctx.stream.emit(chunk.text)


# Operator clicked Send reply on an ask card we'd pushed them. Look up the
# original peer by qid and forward the answer back over A2A.
@app.on_card_action_execute(ASK_REPLY_ACTION)
async def handle_reply_submit(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    d = ctx.activity.value.action.data
    qid = d.get("qid", "")
    answer_text = d.get("answer", "")

    pending = state.inbound_asks.pop(qid, None)
    if pending is None:
        logger.warning("[%s] no pending inbound ask for qid=%s", NAME, qid)
        return AdaptiveCardActionMessageResponse(value="Reply not sent: no matching ask.")

    reply_url = pending["reply_url"]
    sender = pending["sender"]

    reply = ReplyMessage(qid=qid, answer=answer_text, responder=NAME)
    await send_a2a(reply_url, reply.model_dump())
    return AdaptiveCardActionMessageResponse(value=f"Reply sent back to {sender}.")


async def main() -> None:
    # Teams bot and A2A server run side-by-side in the same process.
    a2a_app = make_a2a_app(
        teams_app=app,
        state=state,
        description=DESCRIPTION,
        skill="ask_reply",
        url=SELF_A2A_URL,
        allowed_peer_urls=ALLOWED_PEER_URLS,
        on_peer_reply=bot_agent.record_peer_reply,
    )
    a2a_server = uvicorn.Server(uvicorn.Config(a2a_app.build(), host=A2A_HOST, port=A2A_PORT, log_level="info"))
    await asyncio.gather(app.start(TEAMS_PORT), a2a_server.serve())


if __name__ == "__main__":
    asyncio.run(main())
