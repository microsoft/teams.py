# Sample: MCP Server

Exposes human-in-the-loop (HITL) primitives as MCP tools using the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) SDK. An AI agent can notify users, ask questions, and request approvals — all delivered through Teams using the bot's proactive messaging and Adaptive Card capabilities.

## Setup

```bash
uv sync
cp .env.example .env  # fill in CLIENT_ID, CLIENT_SECRET, TENANT_ID
```

## Run

```bash
uv run python src/main.py
```

The bot listens for Teams activity on `POST /api/messages` (port 3978 by default) and serves the MCP endpoint at `http://localhost:3978/mcp`.

## How it works

The sample is split across five modules:

| File | Responsibility |
|------|---------------|
| `app.py` | `App` instance, Teams activity handlers (`on_message`, `on_card_action_execute`) |
| `mcp_tools.py` | `FastMCP` instance, MCP tool definitions (`@mcp.tool()`) |
| `models.py` | Pydantic result types returned by tools |
| `state.py` | Shared in-memory state (conversation map, pending asks, approvals, async waiters) |
| `main.py` | Entry point — wires the MCP server onto the Teams FastAPI server and starts everything |

Tools are registered with `@mcp.tool()` on the `FastMCP` instance in `mcp_tools.py`. The MCP server is mounted onto the same FastAPI server that handles Teams activity — `app.initialize()` must be called first so `/api/messages` is registered before the catch-all MCP mount at `/`.

### Long-polling pattern

`wait_for_reply` and `wait_for_approval` use **long-polling**: the tool holds the MCP HTTP connection open for up to `timeout_seconds` seconds and returns as soon as the human acts. If the timeout fires before the human responds, the tool returns `status: "pending"` — the agent simply calls the tool again. This keeps the agent in its normal tool-call loop without ever having to "exit and resume":

```
agent calls ask(user_id, "Which region?")          → returns {request_id: "abc"}
agent calls wait_for_reply("abc", timeout=30)       → server parks the connection
  … human types "East US 2" and clicks Send …
  → server wakes up, returns {status: "answered", reply: "East US 2"} immediately
agent reads reply and continues                     → no special resume needed
```

If the human is slow, `wait_for_reply` returns `{status: "pending"}` after 30 s. A well-prompted agent will call it again:

```
agent calls wait_for_reply("abc", timeout=30)   → timeout, returns {status: "pending"}
agent calls wait_for_reply("abc", timeout=30)   → human replies in second window → answer
```

### Ask flow

`ask` records the `PendingAsk` **before** sending the card so a near-instant reply is never lost. It sends an Adaptive Card with a text input field. When the user submits, the `ask_reply` card-action handler updates `pending_asks` and resolves the `asyncio.Future` that `wait_for_reply` is sleeping on — so `wait_for_reply` returns sub-millisecond after the answer lands.

### Approval flow

`request_approval` sends an Adaptive Card with **Approve** and **Reject** buttons and records `approvals[id] = "pending"` before sending. When the user clicks, the `approval_response` card-action handler updates `approvals` and resolves the `asyncio.Future` that `wait_for_approval` is sleeping on.

All tools return structured JSON.

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `notify` | Send a one-way notification to a Teams user | `user_id, message` |
| `ask` | Ask a Teams user a question via Adaptive Card; returns a `request_id` | `user_id, question` |
| `get_reply` | Snapshot current reply state for an ask; returns `pending` until answered | `request_id` |
| `wait_for_reply` | Long-poll until the user replies (or timeout); returns `pending` if timeout fires | `request_id, timeout_seconds=30` |
| `request_approval` | Send an Approve/Reject card; returns an `approval_id` | `user_id, title, description` |
| `get_approval` | Snapshot current approval status: `pending`, `approved`, or `rejected` | `approval_id` |
| `wait_for_approval` | Long-poll until the user decides (or timeout); returns `pending` if timeout fires | `approval_id, timeout_seconds=30` |

> **`wait_for_*` vs `get_*`** — `wait_for_*` holds the HTTP connection open and returns immediately when the human acts, making the agent's tool loop as responsive as possible. `get_*` returns the current snapshot instantly; use it when you want a non-blocking check or to inspect state from outside an agent loop.

## Example agent workflow

```
1. ask("aad-object-id-of-engineer", "Which region should I deploy to?")
   → {request_id: "abc"}

2. wait_for_reply("abc", timeout_seconds=30)
   → server parks; engineer types "East US 2" in Teams and clicks Send
   → {status: "answered", reply: "East US 2"}   ← returns the moment they click

3. agent proceeds with "East US 2"
```

## Limitations

All state (`personal_conversations`, `pending_asks`, `approvals`) is held in memory. A server restart clears everything — pending asks and approvals in flight will be lost. For production use, replace the in-memory dicts with a persistent store (e.g. Redis or a database).

The `user_id` parameter for all tools must be the user's **AAD object ID** (not display name or email). Use your tenant's Azure portal or Microsoft Graph to look up object IDs.

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Open the URL printed in the terminal — it includes a `MCP_PROXY_AUTH_TOKEN` query param that must be present.
2. Set transport to **Streamable HTTP** and URL to `http://localhost:3978/mcp`, then connect.
3. Call `ask` with a real AAD `user_id` → respond in Teams → call `wait_for_reply` to see the answer arrive.


## Setup

```bash
uv sync
cp .env.example .env  # fill in CLIENT_ID, CLIENT_SECRET, TENANT_ID
```

## Run

```bash
uv run python src/main.py
```

The bot listens for Teams activity on `POST /api/messages` (port 3978 by default) and serves the MCP endpoint at `http://localhost:3978/mcp`.

### Ask flow

`ask` sends an Adaptive Card with a text input field. When the user types a reply and clicks **Send**, the `ask_reply` card-action handler fires, updates `pending_asks`, and resolves any `asyncio.Future` registered by `wait_for_reply`. This lets `wait_for_reply` return sub-millisecond after the answer lands instead of polling.

### Approval flow

`request_approval` sends an Adaptive Card with **Approve** and **Reject** buttons. When the user clicks either, the `approval_response` card-action handler updates `approvals` and resolves the `asyncio.Future` registered by `wait_for_approval`.

All tools return structured JSON.

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `notify` | Send a one-way notification to a Teams user | `user_id, message` |
| `ask` | Ask a Teams user a question via Adaptive Card; returns a `request_id` | `user_id, question` |
| `get_reply` | Snapshot current reply state for an ask; returns `pending` until answered | `request_id` |
| `wait_for_reply` | Block until the user replies (or timeout); preferred over polling | `request_id, timeout_seconds=30` |
| `request_approval` | Send an Approve/Reject card; returns an `approval_id` | `user_id, title, description` |
| `get_approval` | Snapshot current approval status: `pending`, `approved`, or `rejected` | `approval_id` |
| `wait_for_approval` | Block until the user decides (or timeout); preferred over polling | `approval_id, timeout_seconds=30` |

> **Prefer `wait_for_*` over `get_*`** — the blocking tools return immediately when the user acts and fall back to the current status on timeout. The polling tools (`get_reply`, `get_approval`) exist for manual inspection or non-blocking workflows.

## Limitations

All state (`personal_conversations`, `pending_asks`, `approvals`) is held in memory. A server restart clears everything — pending asks and approvals in flight will be lost. For production use, replace the in-memory dicts with a persistent store (e.g. Redis or a database).

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Open the URL printed in the terminal — it includes a `MCP_PROXY_AUTH_TOKEN` query param that must be present.
2. Set transport to **Streamable HTTP** and URL to `http://localhost:3978/mcp`, then connect.
3. Call `ask` or `request_approval` with a `user_id`, respond in Teams, then call `wait_for_reply` or `wait_for_approval` to see the result.

