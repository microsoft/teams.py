> [!CAUTION]
> This project is in public preview. We'll do our best to maintain compatibility, but there may be breaking changes in upcoming releases.

# Teams AI Agent (agent-framework)

A Teams bot powered by [agent-framework](https://github.com/microsoft/agent-framework) and Azure OpenAI. Supports streaming responses, inline citations from MCP search results, per-conversation memory, and Microsoft Graph-backed local tools alongside remote MCP servers.

## Features

- **Streaming responses** — text streams token-by-token into Teams as the model generates it
- **Citations** — sources from MCP search tools are attached as clickable references in the reply
- **Conversation memory** — each conversation maintains its own session so the agent remembers context across turns
- **AI-generated label + feedback** — replies include the Teams "AI-generated" label and thumbs up/down feedback buttons; clicking a reaction opens a custom Adaptive Card form for additional feedback
- **Local tools** — Microsoft Graph-backed tools for org directory lookups, org hierarchy, team membership, and presence
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

# Teams bot credentials — also used by Microsoft Graph local tools
CLIENT_ID=<app-id>
TENANT_ID=<tenant-id>
CLIENT_SECRET=<client-secret>
```

`AZURE_OPENAI_MODEL` is the **deployment name** of your model, not the base model name. The bot's Service Principal (`CLIENT_ID`) is used for Teams and Microsoft Graph.

### Microsoft Graph permissions

The local tools call Graph as the bot's service principal (app-only). Grant these **Application** permissions to the app registration in the Azure portal (**Entra ID > App registrations > your app > API permissions**), then click **Grant admin consent**:

| Permission             | Used by                                |
| ---------------------- | -------------------------------------- |
| `User.Read.All`        | `find_people`, `get_org_context`       |
| `Group.Read.All`       | `list_team_members`                    |
| `GroupMember.Read.All` | `list_team_members`                    |
| `Presence.Read.All`    | `get_presence`                         |

### Using a Service Principal for Azure OpenAI instead of an API key

`agent.py` authenticates to Azure OpenAI with `AZURE_OPENAI_API_KEY`. If you'd rather use the bot's Service Principal (so the same identity powers Teams, Graph, and Azure OpenAI), swap `api_key` for a `ClientSecretCredential`:

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

- `Who is <colleague's name>?` — directory lookup via `find_people`
- `Who does <colleague> report to?` — manager + direct reports via `get_org_context`
- `Who's on the <team-name> team?` — group membership via `list_team_members`
- `Is <colleague> available right now?` — Teams presence via `get_presence`
- `Find the manager of <colleague> and tell me if they're online` — chains `get_org_context` and `get_presence`
- `How do I send a proactive message in teams.py?` — searches Microsoft Learn docs (MCP)

## Architecture

```
main.py          — Teams App, message handler, streaming, citations
agent.py         — Agent setup, OpenAIChatClient, AgentMiddleware
local_tools.py   — @tool functions (Microsoft Graph-backed directory lookups)
mcp_tools.py     — MCP server declarations (remote tool servers)
```

`main.py` streams every response with `agent.run(..., stream=True)`. Citations collected during tool calls are attached to the final activity.

`AgentMiddleware` intercepts every tool call to log it and extract citation URLs from MCP search results. Citations are filtered to only those the model actually referenced with `[N]` markers before being attached to the Teams reply.
