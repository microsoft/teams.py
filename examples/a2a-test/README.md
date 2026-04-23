# Sample: Two Teams bots relaying questions via A2A + Adaptive Cards

Two symmetric Teams bots. Either can forward a question to the other over A2A; the answer comes back from a human who fills in an Adaptive Card.

## Flow

```
User-A → Alice                                Bob → Operator-B
"ask bob what color is the sky"
   └─► Alice stashes qid → user's conv       (awaiting_reply)
   └─► A2A ask {qid, question, sender,
                reply_url=Alice}            ──► Bob validates reply_url against
                                                 allowlist, stashes qid →
                                                 {reply_url, sender, question}
                                                 (inbound_asks), builds + pushes
                                                 ask card to Operator-B
                                                      ↓
                                                Operator-B types "blue", clicks Submit
                                                      ↓
                                                Bob's on_card_action_execute:
                                                 pops inbound_asks[qid] for the
                                                 trusted reply_url
                                                      ↓
   Alice ◄── A2A reply {qid, answer,
                        responder} ─────────── Bob sends to the stored reply_url
   └─► Alice pops awaiting_reply[qid], builds + pushes reply card to User-A
```

## Files

- **Bot A / Alice** (`src/bot_a.py`) — Teams on **3978**, A2A on **5000**. Prefix: `ask bob`.
- **Bot B / Bob** (`src/bot_b.py`) — Teams on **3979**, A2A on **5001**. Prefix: `ask alice`.
- **Shared**
  - `src/state.py` — `BotState` (operator conversation, outbound asks awaiting a reply, inbound asks awaiting an operator).
  - `src/a2a_executor.py` — A2A server dispatch: `ask` → validate `reply_url`, stash, push card to operator; `reply` → push card to the original user.
  - `src/a2a_server.py` — `make_a2a_app(..., allowed_peer_urls=...)` wraps the executor in `A2AStarletteApplication`.
  - `src/a2a_client.py` — `send_a2a(peer_url, data)` one-shot sender, plus `is_allowed_peer(url, allowed)` for origin-based peer URL validation.
  - `src/cards.py` — `ask_card(sender, question, qid)` (submit carries only qid), `reply_card(...)`.

## Operator model

Each bot remembers the last **1:1** Teams conversation that messaged it (`state.operator_conv_id`). Incoming asks are pushed into that conversation. 

## Configuration

Create `.env` in `examples/a2a-test/`:

```dotenv
# Shared — your Microsoft tenant
TENANT_ID=<your-tenant-id>

# Bot A (Alice) — Teams app registration
BOT_A_CLIENT_ID=<alice-client-id>
BOT_A_CLIENT_SECRET=<alice-client-secret>

# Bot B (Bob) — Teams app registration
BOT_B_CLIENT_ID=<bob-client-id>
BOT_B_CLIENT_SECRET=<bob-client-secret>

# Optional — ports and A2A peer URLs (defaults shown)
# BOT_A_PORT=3978
# BOT_A_A2A_HOST=localhost
# BOT_A_A2A_PORT=5000
# BOB_A2A_URL=http://localhost:5001/
# BOT_B_PORT=3979
# BOT_B_A2A_HOST=localhost
# BOT_B_A2A_PORT=5001
# ALICE_A2A_URL=http://localhost:5000/
```

Each bot needs its **own** Teams app registration so DMs route to the right bot. If any `BOT_X_CLIENT_*` is empty, the bot falls back to the generic `CLIENT_ID` / `CLIENT_SECRET` — fine for devtools, but Teams can only route DMs to one bot at a time.

## Run

Two terminals from `examples/a2a-test/`:

```bash
uv run python src/bot_a.py   # Alice — Teams 3978, A2A 5000
uv run python src/bot_b.py   # Bob   — Teams 3979, A2A 5001
```

> ⚠ **DM each bot once before relaying.** The operator's conversation id is captured from the first Teams message the bot receives. If you `ask bob …` before Bob has been DM'd, Bob will log `no operator conversation; ask not pushed` and the card won't appear anywhere.