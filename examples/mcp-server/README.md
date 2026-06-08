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

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Open the URL printed in the terminal — it includes a `MCP_PROXY_AUTH_TOKEN` query param that must be present.
2. Set transport to **Streamable HTTP** and URL to `http://localhost:3978/mcp`, then connect.
3. Call `ask` with a real AAD `user_id` → respond in Teams → call `wait_for_reply` to see the answer arrive.