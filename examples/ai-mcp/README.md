> [!CAUTION]
> This project is in public preview. We'll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Teams AI Agent with MCP tools

A Teams bot powered by [agent-framework](https://github.com/microsoft/agent-framework) and Azure OpenAI. It streams responses token-by-token, attaches inline citations from MCP search results, asks clarifying questions via Adaptive Cards, and suggests follow-up questions after each reply.

## Features

- **Streaming responses** — text streams token-by-token into Teams as the model generates it.
- **Citations** — sources from MCP search tools are attached as clickable references in the reply; only citations actually referenced with `[N]` markers in the text are included.
- **Conversation memory** — each conversation maintains its own `AgentSession` so the agent remembers context across turns.
- **AI-generated label + custom feedback** — replies include the Teams "AI-generated" label and thumbs up/down feedback buttons; clicking a reaction opens a custom Adaptive Card form for additional feedback.
- **Clarification cards** — when the user's request is ambiguous, the agent calls `request_clarification` to present a choice card; the user's selection feeds back into the same session as the next turn.
- **Dynamic follow-up suggestions** — after each reply a second lightweight OpenAI call generates two contextual follow-up questions shown as suggested-action buttons.
- **MCP tools** — remote tool servers: Microsoft Learn docs search (`MCPStreamableHTTPTool`).

## Prerequisites

- Python >= 3.12, < 3.15
- UV >= 0.8.11
- An Azure OpenAI resource with a deployed model
- A Teams bot registration (App ID + password)

## Setup

Create a `.env` file in `examples/ai-mcp/`:

```env
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
AZURE_OPENAI_MODEL=<deployment-name>
AZURE_OPENAI_API_KEY=<api-key>

# Teams bot credentials
CLIENT_ID=<app-id>
TENANT_ID=<tenant-id>
CLIENT_SECRET=<client-secret>
```

`AZURE_OPENAI_MODEL` is the **deployment name** of your model, not the base model name.

### Using a Service Principal for Azure OpenAI instead of an API key

`agent.py` authenticates to Azure OpenAI with `AZURE_OPENAI_API_KEY`. If you'd rather use the bot's Service Principal, swap `api_key` for a `ClientSecretCredential`:

```python
from azure.identity import ClientSecretCredential

client = OpenAIChatClient(
    model=getenv("AZURE_OPENAI_MODEL"),
    azure_endpoint=getenv("AZURE_OPENAI_ENDPOINT"),
    credential=ClientSecretCredential(
        tenant_id=getenv("TENANT_ID"),
        client_id=getenv("CLIENT_ID"),
        client_secret=getenv("CLIENT_SECRET"),
    ),
)
```

Then drop `AZURE_OPENAI_API_KEY` from `.env` and grant the Service Principal the **Azure AI User** role on the Azure OpenAI resource.

### Teams bot registration

Follow the standard Teams bot setup to get a bot App ID and password, and configure the messaging endpoint to point at this bot (e.g. via [Dev Tunnels](https://learn.microsoft.com/azure/developer/dev-tunnels/overview) for local development).

## Running

```bash
cd examples/ai-mcp
uv run src/main.py
```

## Example interactions

Once the bot is running in a Teams chat, try:

- `How do I stream responses in teams.py?` — searches Microsoft Learn docs (MCP) with inline citations and two follow-up suggestions.
- `How do I send a proactive message in teams.py?` — same, different topic.
- `Tell me about cards` — ambiguous enough that the agent may call `request_clarification`, presenting a choice card. Pick an option to continue.

## Architecture

```
main.py          — Teams App, message/card-action handlers, streaming, citations, follow-ups, feedback
agent.py         — Agent setup, OpenAIChatClient, AgentMiddleware (citation extraction)
local_tools.py   — @tool: request_clarification (Adaptive Card choice prompt)
mcp_tools.py     — MCPStreamableHTTPTool declarations (remote MCP servers)
```

### Request flow

1. `handle_message` creates or reuses an `AgentSession` for the conversation, resets `pending_cards` and `tool_logger.citations`, then calls `agent.run(..., stream=True)`.
2. Text chunks are streamed to Teams via `ctx.stream.emit`.
3. If `request_clarification` fires, it appends an `AdaptiveCard` to `pending_cards` — the final emit sends the card only (no text, no feedback).
4. Otherwise `_generate_follow_ups` makes a lightweight structured-output call and `_build_reply` assembles the `MessageActivityInput` with the AI-generated label, custom feedback, filtered citations, and suggested-action buttons.
5. When the user picks a clarification option the `ask_reply` card-action handler feeds the choice back into the same session as a new turn.

### `AgentMiddleware`

`AgentMiddleware` (a `FunctionMiddleware`) intercepts every tool call to log it and extract citation metadata from MCP search results (fields `contentUrl`/`link`, `title`, `content`). Each citation is assigned a `[N]` marker injected back into the tool result so the model can reference it inline. `_attach_citations` then filters down to only the positions the model actually used before attaching them to the reply.
