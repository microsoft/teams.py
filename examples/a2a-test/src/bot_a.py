"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
import uuid
from os import getenv

import uvicorn
from a2a_client import send_a2a
from a2a_server import make_a2a_app
from cards import ASK_REPLY_ACTION, ask_card, reply_card
from dotenv import load_dotenv
from microsoft_teams.api import AdaptiveCardInvokeActivity, MessageActivity, TypingActivityInput
from microsoft_teams.api.models.adaptive_card import AdaptiveCardActionMessageResponse
from microsoft_teams.api.models.invoke_response import AdaptiveCardInvokeResponse
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.common import ConsoleFormatter
from state import BotState

"""

Bot A (Alice) — Teams bot + A2A server + async A2A sender.

- Teams: port 3978. A2A: port 5000.
- `ask bob <q>` → send ask card to Bob over A2A, return immediately.
- Bob's operator fills in the card and clicks Send reply → Bob's card-action
  handler routes the reply back over A2A. Alice pushes the reply card to the
  user who originally asked.
- When Alice receives an ask from Bob, her executor pushes the ask card into
  Alice's own current operator conversation. That operator fills in the card
  and clicks Send reply → Alice's card-action handler sends the reply back.
"""
load_dotenv()


NAME = "Alice"
TEAMS_PORT = int(getenv("BOT_A_PORT", "3978"))
A2A_HOST = getenv("BOT_A_A2A_HOST", "localhost")
A2A_PORT = int(getenv("BOT_A_A2A_PORT", "5000"))
SELF_A2A_URL = f"http://{A2A_HOST}:{A2A_PORT}/"
PEER_URL = getenv("BOB_A2A_URL", "http://localhost:5001/")
PEER_PREFIX = "ask bob "

logging.getLogger().setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(ConsoleFormatter())
logging.getLogger().addHandler(_handler)

app = App(
    client_id=getenv("BOT_A_CLIENT_ID"),
    client_secret=getenv("BOT_A_CLIENT_SECRET"),
    tenant_id=getenv("TENANT_ID"),
)
state = BotState(name=NAME)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.reply(TypingActivityInput())
    text = (ctx.activity.text or "").strip()
    state.operator_conv_id = ctx.activity.conversation.id

    if text.lower().startswith(PEER_PREFIX):
        question = text[len(PEER_PREFIX) :].strip()
        qid = str(uuid.uuid4())
        card = ask_card(sender=NAME, question=question, qid=qid, reply_url=SELF_A2A_URL)

        state.awaiting_reply[qid] = {
            "conv_id": ctx.activity.conversation.id,
            "question": question,
        }
        await send_a2a(
            PEER_URL,
            {
                "kind": "ask",
                "qid": qid,
                "question": question,
                "sender": NAME,
                "reply_url": SELF_A2A_URL,
                "card": card.model_dump(by_alias=True, exclude_none=True),
            },
        )
        await ctx.send(f"Asked peer (qid {qid[:8]}). Waiting for reply…")
        return

    await ctx.send("hi")


@app.on_card_action_execute(ASK_REPLY_ACTION)
async def handle_reply_submit(ctx: ActivityContext[AdaptiveCardInvokeActivity]) -> AdaptiveCardInvokeResponse:
    d = ctx.activity.value.action.data
    qid = d.get("qid", "")
    question = d.get("question", "")
    reply_url = d.get("reply_url", "")
    answer_text = d.get("answer", "")

    card = reply_card(responder=NAME, question=question, answer=answer_text, qid=qid)
    await send_a2a(
        reply_url,
        {
            "kind": "reply",
            "qid": qid,
            "question": question,
            "answer": answer_text,
            "card": card.model_dump(by_alias=True, exclude_none=True),
        },
    )
    return AdaptiveCardActionMessageResponse(
        status_code=200,
        type="application/vnd.microsoft.activity.message",
        value=f"Reply sent back to {d.get('sender', 'peer')}.",
    )


async def main() -> None:
    a2a_app = make_a2a_app(
        teams_app=app,
        state=state,
        description=f"{NAME} asks and answers over A2A.",
        skill="ask_reply",
        url=SELF_A2A_URL,
    )
    a2a_server = uvicorn.Server(uvicorn.Config(a2a_app.build(), host=A2A_HOST, port=A2A_PORT, log_level="info"))
    await asyncio.gather(app.start(TEAMS_PORT), a2a_server.serve())


if __name__ == "__main__":
    asyncio.run(main())
