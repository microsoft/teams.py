# Sample: MCP Server

Exposes human-in-the-loop primitives as MCP tools using the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) SDK. An AI agent can notify users, ask questions, and request approvals — all delivered through Teams using the bot's proactive messaging and Adaptive Card capabilities.

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

The sample is split across four modules:

| File | Responsibility |
|------|---------------|
| `app.py` | `App` instance, Teams activity handlers (`on_message`, `on_card_action_execute`) |
| `mcp_tools.py` | `FastMCP` instance, MCP tool definitions (`@mcp.tool()`) |
| `state.py` | Shared in-memory state (conversation map, pending asks, approvals) |
| `main.py` | Entry point — wires the MCP server onto the Teams FastAPI server and starts everything |

Tools are registered with `@mcp.tool()` on the `FastMCP` instance in `mcp_tools.py`. The MCP server is mounted onto the same FastAPI server that handles Teams activity — `app.initialize()` must be called first so `/api/messages` is registered before the catch-all MCP mount at `/`.

The bot handler (`on_message`) captures user replies to pending asks. Approval decisions are captured via `on_card_action_execute` when the user clicks Approve or Reject on the card. Both are surfaced to the MCP client via the polling tools.

All tools return JSON.

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `notify` | Send a one-way notification to a Teams user | `user_id, message` |
| `ask` | Ask a Teams user a question; returns a `request_id` | `user_id, question` |
| `get_reply` | Poll for the user's reply to an `ask`; returns `pending` until answered | `request_id` |
| `request_approval` | Send an Approve/Reject card to a Teams user; returns an `approval_id` | `user_id, title, description` |
| `get_approval` | Poll for the approval decision: `pending`, `approved`, or `rejected` | `approval_id` |

## Example agent workflow

1. `request_approval` — agent sends "Can you approve deployment to prod?" to an on-call engineer
2. Engineer clicks **Approve** on the card in Teams
3. `get_approval` — agent reads `"approved"` and proceeds with the deployment

## Limitations

All state (`personal_conversations`, `pending_asks`, `approvals`) is held in memory. A server restart clears everything — pending asks and approvals in flight will be lost. For production use, replace the in-memory dicts with a persistent store (e.g. Redis or a database).

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Open the URL printed in the terminal — it includes a `MCP_PROXY_AUTH_TOKEN` query param that must be present.
2. Set transport to **Streamable HTTP** and URL to `http://localhost:3978/mcp`, then connect.
3. Call `ask` or `request_approval` with a `user_id`, then respond in Teams and poll for the result.
