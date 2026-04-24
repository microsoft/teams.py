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

# Bot A (Alice) — Teams bot + A2A server, with an LLM that decides per-turn
# whether to answer directly or forward the user's question to a peer over A2A.
#
# - Teams: port 3978. A2A: port 5000.
# - Inbound user message → agent.run() streams reply; the agent may call the
#   `send_to_peer` tool, which queues an A2A ask to Bob.
# - When Bob's operator answers, Bob sends a reply over A2A. Alice's executor
#   pushes a reply card to the user *and* injects a "[peer update]" note into
#   the user's session so the next LLM turn knows about it.
# - When Alice receives an ask from Bob, her executor pushes an ask card into
#   Alice's current operator's 1:1 conversation. The operator fills it in and
#   submits → Alice's card-action handler sends the reply back over A2A.
load_dotenv()


NAME = "Alice"
TEAMS_PORT = int(getenv("BOT_A_PORT", "3978"))
A2A_HOST = getenv("BOT_A_A2A_HOST", "localhost")
A2A_PORT = int(getenv("BOT_A_A2A_PORT", "5000"))
SELF_A2A_URL = f"http://{A2A_HOST}:{A2A_PORT}/"
BOB_URL = getenv("BOB_A2A_URL", "http://localhost:5001/")
ALLOWED_PEER_URLS = [BOB_URL]

logging.getLogger().setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(ConsoleFormatter())
logging.getLogger().addHandler(_handler)
logger = logging.getLogger(__name__)

app = App(
    client_id=getenv("BOT_A_CLIENT_ID"), client_secret=getenv("BOT_A_CLIENT_SECRET"), tenant_id=getenv("TENANT_ID")
)
state = BotState(name=NAME)
bot_agent = BotAgent(self_name=NAME, self_a2a_url=SELF_A2A_URL, peers={"bob": BOB_URL}, state=state)

# Description goes into Alice's A2A AgentCard. Peers' LLMs read it to
# decide whether to forward a question. Tweak to match your scenario.
DESCRIPTION = "Alice — a Teams bot whose human operator answers design and UX questions."


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
