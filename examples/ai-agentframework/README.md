> [!CAUTION]
> This project is in public preview. We'll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Teams AI Agent (agent-framework)

A Teams bot powered by [agent-framework](https://github.com/microsoft/agent-framework) and Azure OpenAI. Supports streaming responses, inline citations from MCP search results, per-conversation memory, and a adaptive-card local tool alongside remote MCP servers.

## Features

- **Streaming responses** — text streams token-by-token into Teams as the model generates it
- **Citations** — sources from MCP search tools are attached as clickable references in the reply
- **Conversation memory** — each conversation maintains its own session so the agent remembers context across turns
- **AI-generated label + custom feedback** — replies include the Teams "AI-generated" label and thumbs up/down feedback buttons; clicking a reaction opens a custom Adaptive Card form for additional feedback
- **Welcome card tool** — a local `@tool` the agent calls to greet users with an Adaptive Card
- **MCP tools** — remote tool servers: Microsoft Learn docs search

## Prerequisites

- Python >= 3.12, < 3.15
- UV >= 0.8.11
- An Azure OpenAI resource with a deployed model
- A Teams bot registration (App ID + password)

## Setup

Create a `.env` file in `examples/ai-agentframework/`:

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
cd examples/ai-agentframework
uv run src/main.py
```

## Example interactions

Once the bot is running in a Teams chat, try:

- `Hi! My name is Alex !` — agent calls `send_welcome_card` and greets you with an Adaptive Card
- `How do I stream in teams.py?` — searches Microsoft Learn docs (MCP) with inline citations
- `How do I send a proactive message in teams.py?` — searches Microsoft Learn docs (MCP) with inline citations

## Architecture

```
main.py          — Teams App, message handler, streaming, citations, card attachment
agent.py         — Agent setup, OpenAIChatClient, AgentMiddleware
local_tools.py   — @tool functions (welcome card)
mcp_tools.py     — MCP server declarations (remote tool servers)
```

`main.py` streams every response with `agent.run(..., stream=True)`. Citations collected during tool calls, and any cards queued by local tools, are attached to the final activity.

`AgentMiddleware` intercepts every tool call to log it and extract citation URLs from MCP search results. Citations are filtered to only those the model actually referenced with `[N]` markers before being attached to the Teams reply.
