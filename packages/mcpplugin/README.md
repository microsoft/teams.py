# Microsoft Teams MCP Plugin

<p>
    <a href="https://pypi.org/project/microsoft-teams-mcpplugin/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-mcpplugin" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-mcpplugin/" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-mcpplugin" />
    </a>
</p>

Model Context Protocol (MCP) integration for Microsoft Teams AI applications.
Enables Teams bots to both expose tools as MCP servers and use MCP servers as clients.

[📖 Documentation](https://microsoft.github.io/teams-ai/python/in-depth-guides/ai/mcp/)

## Installation

```bash
uv add microsoft-teams-mcpplugin
```

## Usage

### MCP Client (Use MCP Servers)

```python
from microsoft.teams.apps import App
from microsoft.teams.mcpplugin import McpClientPlugin

app = App()

# Connect to an MCP server
mcp_client = McpClientPlugin(
    server_command="uvx",
    server_args=["mcp-server-time"]
)

app.use(mcp_client)
```

### MCP Server (Expose Tools)

```python
from microsoft.teams.apps import App
from microsoft.teams.mcpplugin import McpServerPlugin
from microsoft.teams.ai import Function
from pydantic import BaseModel

app = App()

class EchoParams(BaseModel):
    message: str

async def echo_handler(params: EchoParams) -> str:
    return f"Echo: {params.message}"

# Expose app as MCP server
mcp_server = McpServerPlugin(name="my-mcp-server")
app.use(mcp_server)
```
