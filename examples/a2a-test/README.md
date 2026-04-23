# Sample: Two Teams bots relaying questions via A2A + Adaptive Cards

Two symmetric Teams bots. Either can forward a question to the other over A2A; the answer comes back from a human who fills in an Adaptive Card.

## Flow

```
User-A → Alice                                Bob → Operator-B
"ask bob what color is the sky"
   └─► Alice stashes qid → user's conv
   └─► A2A ask {qid, reply_url=Alice, card} ──► Bob pushes ask card to Operator-B
                                                  (card has TextInput + Submit,
                                                   submit carries qid + reply_url)
                                                      ↓
                                                Operator-B types "blue", clicks Submit
                                                      ↓
                                                Bob's on_card_action_execute handler
                                                      ↓
   Alice ◄── A2A reply {qid, card} ──────────── Bob sends reply card to reply_url
   └─► Alice looks up qid, pushes reply card to User-A
```

The ask card carries its own routing metadata (qid, sender, reply_url) in the submit-action data, so the receiving bot stores **no per-question state** — the card is the state.

## Files

- **Bot A / Alice** (`src/bot_a.py`) — Teams on **3978**, A2A on **5000**. Prefix: `ask bob`.
- **Bot B / Bob** (`src/bot_b.py`) — Teams on **3979**, A2A on **5001**. Prefix: `ask alice`.
- **Shared**
  - `src/state.py` — `BotState` (operator conversation + outbound asks awaiting a reply).
  - `src/a2a_executor.py` — A2A server dispatch: `ask` → push card to operator; `reply` → push card to the original user.
  - `src/a2a_server.py` — `make_a2a_app(...)` wraps the executor in `A2AStarletteApplication`.
  - `src/a2a_client.py` — `send_a2a(peer_url, data)` one-shot sender.
  - `src/cards.py` — `ask_card(...)` (TextInput + ExecuteAction carrying qid/reply_url), `reply_card(...)`.

## Operator model

Each bot remembers the last Teams conversation that messaged it (`state.operator_conv_id`). Incoming asks are pushed into that conversation. **DM each bot once before relaying asks**, so it has a conversation id.

## Run

Two terminals from `examples/a2a-test/`:

```bash
uv run python src/bot_a.py   # Alice — Teams 3978, A2A 5000
uv run python src/bot_b.py   # Bob   — Teams 3979, A2A 5001
```

> ⚠ **DM each bot once before relaying.** The operator's conversation id is captured from the first Teams message the bot receives. If you `ask bob …` before Bob has been DM'd, Bob will log `no operator conversation; ask not pushed` and the card won't appear anywhere.

## Bot registrations

Each bot needs its own Teams app registration for separate DM routing. Set `BOT_A_CLIENT_ID`/`BOT_A_CLIENT_SECRET` and `BOT_B_CLIENT_ID`/`BOT_B_CLIENT_SECRET` in `.env`. If empty, both fall back to `CLIENT_ID`/`CLIENT_SECRET` (fine for devtools, but Teams can only route DMs to one at a time).
