# Sample: MCP Server

Exposes Teams bot functionality as MCP tools using the official [`mcp`](https://github.com/modelcontextprotocol/python-sdk) SDK. Tools are registered with the `@mcp.tool()` decorator and served over streamable HTTP at `/mcp`.

## Setup

```bash
uv sync
cp .env.example .env  # fill in CLIENT_ID, CLIENT_SECRET, TENANT_ID
```

## Run

```bash
uv run python src/main.py
```

The bot listens for Teams messages on `POST /api/messages` (port 3978 by default) and serves the MCP endpoint at `http://localhost:3978/mcp`.

## How it works

Tools are registered with `@mcp.tool()` directly on a `FastMCP` instance. The MCP server is mounted onto the same FastAPI server that handles Teams activity — `app.initialize()` must be called first so `/api/messages` is registered before the catch-all MCP mount at `/`.

Tool names, descriptions, and input schemas are inferred from the function name, docstring, and type annotations — no separate schema models needed.

## Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `send_message` | Send a proactive message to a Teams user. Creates a new conversation if one does not exist yet. | `user_id, message` |
| `update_message` | Update a bot-sent message by its activity_id | `activity_id, message` |
| `delete_message` | Delete a bot-sent message by its activity_id | `activity_id` |
| `add_reaction` | Add a reaction to a user message by its activity_id | `activity_id, reaction` |
| `remove_reaction` | Remove a reaction from a user message by its activity_id | `activity_id, reaction` |
| `get_members` | List all members of a conversation | `conversation_id` |

`send_message` prints the `activity_id` of the sent message — use that value with `update_message` and `delete_message`. `add_reaction` and `remove_reaction` require an `activity_id` from a user message printed by the bot on receipt.

Valid reactions: `like`, `heart`, `1f440_eyes`, `2705_whiteheavycheckmark`, `launch`, `1f4cc_pushpin`.

## Testing with MCP Inspector

```bash
npx @modelcontextprotocol/inspector
```

1. Open the URL printed in the terminal — it includes a `MCP_PROXY_AUTH_TOKEN` query param that must be present.
2. Set transport to **Streamable HTTP** and URL to `http://localhost:3978/mcp`, then connect.
3. Call `send_message` with a `user_id` and a message.
