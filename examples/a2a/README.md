# Sample: A2A handoff between two Teams bots

Two Teams bots — **Alice** and **Bob** — each backed by an `agent_framework` LLM agent. The user DMs one of them; the agent decides whether to answer directly or hand the user off to the other bot over the [A2A protocol](https://google.github.io/A2A/).

This sample demonstrates:

- **Direct user handoff** — the receiving bot proactively opens a 1:1 DM with the user and greets them with context from the handoff, so the conversation continues seamlessly.
- **Persistent per-conversation history** — `agent_framework` `AgentSession` keeps LLM history per Teams conversation; `asyncio.Lock` serialises concurrent turns.

## Flow

```
User-A    Alice (LLM)               Bob (A2A executor + LLM)
  |           |                                |
  |- "best    |                                |
  |  dog      | LLM: "dogs → Bob".             |
  |  breed?" >| Calls handoff_to_peer          |
  |           |--- A2A handoff ---------------->|
  |           |  (DataPart carries aadObjectId,| Client(serviceUrl).conversations.create()
  |           |   tenantId, serviceUrl,        |   → new 1:1 conv with the user
  |           |   summary)                     |  agent.greetWithHandoff()
  |           |<------- ack -------------------|   → seeds history + greeting
  |<- "I've handed you to Bob"                 |  app.send(newConvId, greeting)
  |                                            |
  |   (Bob's DM lights up with a new message)  |
  |- reply --->|<- delivered in Bob's DM ------|
  |            | LLM sees seeded history, picks up coherently
```

## How it works

1. User DMs **Alice**. Alice's LLM has a single
   `handoff_to_peer(summary)` tool. Its description carries Bob's live
   A2A `AgentCard.description`, fetched once at startup, so the LLM
   knows what Bob actually specializes in.
2. When the LLM decides Bob is a better fit, it calls the tool.
   `runTools()` invokes the callback, which sends an A2A `message/send`
   to Bob with a `DataPart` carrying:
   ```ts
   { kind: 'handoff', from, aadObjectId, userName, tenantId, serviceUrl, summary }
   ```
3. Bob's `HandoffAgentExecutor` validates the payload, then constructs
   a `Client` from `@microsoft/teams.api` against the user's `serviceUrl`
   and calls `conversations.create({...})` to open a 1:1 with the user.
   The member id is the user's **`aadObjectId`**, not the Teams MRI
   (`29:...`) that other samples use — MRIs are bot-specific, so the
   one Alice sees for the user isn't valid against Bob. `aadObjectId`
   is the tenant-wide identity both bots share.
4. Bob's agent runs the LLM with the handoff context as a synthetic
   user turn, producing a greeting that already answers the question.
   The turn is left in the per-conversation history, so when the user
   replies in their new DM, Bob picks up coherently.
5. Bob sends the greeting via `app.send(newConvId, greeting)`.

The bots are symmetric — the same flow runs in reverse from Bob to Alice.

## Configuration

Both bots run the **same code** — differentiated entirely by environment variables. Create two `.env` files (or set env vars) in `examples/a2a/`:

**.env.alice**
```dotenv
# Teams app registration for Alice
BOT_APP_ID=<alice-client-id>
BOT_APP_PASSWORD=<alice-client-secret>
TENANT_ID=<your-tenant-id>

# Bot identity
BOT_NAME=Alice
BOT_DESCRIPTION=General assistant specialising in front-end development and UX
BOT_SELF_URL=https://<alice-public-host>   # used for the A2A AgentCard URL
PEER_NAME=Bob
PEER_URL=https://<bob-public-host>         # A2A CardResolver fetches /.well-known/agent-card.json here

# LLM
AZURE_OPENAI_ENDPOINT=<endpoint>
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_MODEL=<deployment-name>

PORT=3978
```

**.env.bob**
```dotenv
BOT_APP_ID=<bob-client-id>
BOT_APP_PASSWORD=<bob-client-secret>
TENANT_ID=<your-tenant-id>

BOT_NAME=Bob
BOT_DESCRIPTION=Backend and infrastructure specialist — databases, scaling, DevOps
BOT_SELF_URL=https://<bob-public-host>
PEER_NAME=Alice
PEER_URL=https://<alice-public-host>

AZURE_OPENAI_ENDPOINT=<endpoint>
AZURE_OPENAI_API_KEY=<key>
AZURE_OPENAI_MODEL=<deployment-name>

PORT=3979
```

Each bot needs its **own** Teams app registration so DMs are routed to the right bot.

## Run

Two terminals from `examples/a2a/`:

```bash
# Terminal 1 — Alice on port 3978
dotenv -f .env.alice run -- uv run python src/main.py

# Terminal 2 — Bob on port 3979
dotenv -f .env.bob run -- uv run python src/main.py
```

Each bot exposes:
- `POST /api/messages` — Teams traffic (registered by teams.ts on the
  shared Express app)
- `POST /a2a` — inbound A2A JSON-RPC
- `GET  /.well-known/agent-card.json` — the bot's A2A AgentCard

The two bots talk to each other on `localhost` for A2A. For Teams
itself, expose each bot's port through a tunnel (ngrok / dev tunnels)
and register that URL as the bot's messaging endpoint in Azure.

## Caveats

- **Same-tenant assumption.** The handoff carries `aadObjectId` +
  `tenantId` + `serviceUrl`. Bob uses these to call `conversations.create`
  in his own bot context. Cross-tenant handoff would need an OAuth flow
  and identity translation that this sample doesn't cover.
- **Peer must be installed for the user.** A proactive
  `conversations.create` only succeeds if the receiving bot is
  installable for that user (tenant app catalog, user installed, etc.).
  If Bob isn't installed, the create call fails and no DM opens.
- **No auth on `/a2a`.** This sample uses
  `UserBuilder.noAuthentication`, so any caller can post a handoff
  message. For production, validate the caller's identity (bearer
  token or mTLS) before opening a conversation with someone they named.
- **Provider scope.** The agent is bound to the OpenAI chat-completions
  wire protocol — Azure OpenAI and vanilla OpenAI work; non-OpenAI
  providers do not.