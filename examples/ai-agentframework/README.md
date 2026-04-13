> [!CAUTION]
> This project is in public preview. We'll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Teams AI Agent (agent-framework)

A Teams bot powered by [agent-framework](https://github.com/microsoft/agent-framework) and Azure AI Foundry. Supports streaming responses, inline citations from MCP search results, per-conversation memory, and extensible local and remote tools.

## Features

- **Streaming responses** — text streams token-by-token into Teams as the model generates it
- **Citations** — sources from MCP search tools are attached as clickable references in the reply
- **Conversation memory** — each conversation maintains its own session so the agent remembers context across turns
- **AI-generated label + feedback** — replies include the Teams "AI-generated" label and thumbs up/down feedback buttons
- **Local tools** — deterministic utilities the model can call: datetime, math, random selection, exchange rates
- **MCP tools** — remote tool servers: Microsoft Learn docs search, Adaptive Cards MCP

## Prerequisites

- Python >= 3.12
- UV >= 0.8.11
- Node.js (for MCP stdio servers)
- An [Azure AI Foundry](https://ai.azure.com) project with a deployed model
- A Teams bot registration (App ID + password)

## Setup

Create a `.env` file in `examples/ai-agentframework/` (or copy from `sample.env`):

```env
# Azure AI Foundry
PROJECT_ENDPOINT=https://<your-project>.services.ai.azure.com/api/projects/<project-name>
AZURE_OPENAI_MODEL=gpt-4o-mini

# Azure credentials for DefaultAzureCredential (service principal)
# Alternatively, run `az login` or `azd auth login` to use your CLI credentials
AZURE_CLIENT_ID=<app-id>
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_SECRET=<client-secret>
```

### Azure AI Foundry permissions

The identity used (service principal or CLI user) needs the **Azure AI User** role assigned at the **hub** level in Azure AI Foundry.

### Teams bot registration

Follow the standard Teams bot setup to get a bot App ID and password, and configure the messaging endpoint to point at this bot (e.g. via [Dev Tunnels](https://learn.microsoft.com/azure/developer/dev-tunnels/overview) for local development).

## Running

```bash
cd examples/ai-agentframework
uv run src/main.py
```

## Local Tools

| Tool                   | Description                                   |
| ---------------------- | --------------------------------------------- |
| `get_current_datetime` | Current date and time for any UTC offset      |
| `calculate`            | Evaluate mathematical expressions accurately  |
| `random_pick`          | Randomly select one or more items from a list |
| `get_exchange_rate`    | Live currency conversion via frankfurter.app  |

## MCP Tools

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

`AgentMiddleware` intercepts every tool call to log it and extract citation URLs from MCP search results. Citations are filtered to only those the model actually referenced with `[N]` markers before being attached to the Teams reply.
