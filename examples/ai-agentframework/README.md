> [!CAUTION]
> This project is in public preview. We'll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Teams AI Agent (agent-framework)

A Teams bot powered by [agent-framework](https://github.com/microsoft/agent-framework) and Azure AI Foundry. Supports streaming responses, inline citations from MCP search results, per-conversation memory, and extensible local and remote tools.

## Features

- **Streaming responses** — text streams token-by-token into Teams as the model generates it
- **Adaptive Cards** — prefix a message with `/card` to get a structured card response instead of text
- **Citations** — sources from MCP search tools are attached as clickable references in the reply
- **Conversation memory** — each conversation maintains its own session so the agent remembers context across turns
- **AI-generated label + feedback** — replies include the Teams "AI-generated" label and thumbs up/down feedback buttons; clicking a reaction opens a custom Adaptive Card form for additional feedback
- **Local tools** — deterministic utilities the model can call: datetime, math, random selection, exchange rates
- **MCP tools** — remote tool servers: Microsoft Learn docs search, Adaptive Cards MCP

## Prerequisites

- Python >= 3.12, < 3.15 
- UV >= 0.8.11
- Node.js (for MCP stdio servers)
- An [Azure AI Foundry](https://ai.azure.com) project with a deployed model
- A Teams bot registration (App ID + password)

## Setup

Create a `.env` file in `examples/ai-agentframework/`:

```env
# Azure AI Foundry
PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project-name>
AZURE_OPENAI_MODEL=gpt-4o-mini

# Teams bot credentials — also used to authenticate to Azure AI Foundry
CLIENT_ID=<app-id>
TENANT_ID=<tenant-id>
CLIENT_SECRET=<client-secret>
```

The bot's Service Principal (`CLIENT_ID`) is used for both Teams and Azure AI Foundry — no separate Foundry credentials needed.

### Azure AI Foundry permissions

The bot's Service Principal needs the **Azure AI User** role on the Foundry project:

```bash
az role assignment create \
  --role "Azure AI User" \
  --assignee $CLIENT_ID \
  --scope <project-resource-id>
```

To find the resource ID, open the project in the [Azure portal](https://portal.azure.com) and copy it from **Settings > Properties > Resource ID**, or run:

```bash
az cognitiveservices account show --name <foundry-hub-name> -g <resource-group> --query id -o tsv
```

`<hub-name>` is the subdomain of your `PROJECT_ENDPOINT` — e.g. for `https://my-hub.services.ai.azure.com/...` it is `my-hub`.

### Teams bot registration

Follow the standard Teams bot setup to get a bot App ID and password, and configure the messaging endpoint to point at this bot (e.g. via [Dev Tunnels](https://learn.microsoft.com/azure/developer/dev-tunnels/overview) for local development).

## Running

```bash
cd examples/ai-agentframework
uv run src/main.py
```

## Tools

### Local

| Tool                   | Description                                   |
| ---------------------- | --------------------------------------------- |
| `get_current_datetime` | Current date and time for any UTC offset      |
| `calculate`            | Evaluate mathematical expressions accurately  |
| `random_pick`          | Randomly select one or more items from a list |
| `get_exchange_rate`    | Live currency conversion via frankfurter.app  |

### MCP

| Tool            | Type            | Credentials |
| --------------- | --------------- | ----------- |
| `MSLearn`       | Streamable HTTP | None        |
| `AdaptiveCards` | Stdio (npx)     | None        |

> **Note:** For best performance, pre-install the AdaptiveCards MCP server globally to avoid npx cold-start delays:
>
> ```bash
> npm install -g adaptive-cards-mcp
> ```

## Architecture

```
main.py          — Teams App, message handler, streaming, citations
agent.py         — Agent setup, FoundryChatClient, AgentMiddleware
local_tools.py   — @tool functions (deterministic local utilities)
mcp_tools.py     — MCP server declarations (remote tool servers)
```

`main.py` routes incoming messages across two paths:

- **Text path** — streams the response token-by-token using `agent.run(..., stream=True)`. Citations collected during tool calls are attached to the final activity.
- **Card path** — triggered by the `/card` prefix. Runs `agent.run` with `response_format=json_object` (non-streaming) and renders the JSON response as an Adaptive Card attachment.

`AgentMiddleware` intercepts every tool call to log it and extract citation URLs from MCP search results. Citations are filtered to only those the model actually referenced with `[N]` markers before being attached to the Teams reply.
