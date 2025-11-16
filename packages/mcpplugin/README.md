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

[📖 Documentation](https://microsoft.github.io/teams-sdk/python/in-depth-guides/ai/mcp/)

## Installation

```bash
uv add microsoft-teams-mcpplugin
```

## Usage

### MCP Client (Use MCP Servers)

```python
from microsoft.teams.apps import App
from microsoft.teams.mcpplugin import McpClientPlugin
from microsoft.teams.ai import ChatPrompt
from microsoft.teams.openai import OpenAICompletionsAIModel

# Create MCP client plugin
mcp_client = McpClientPlugin()

# Connect to MCP servers
mcp_client.use_mcp_server("https://example.com/mcp")

# Use with ChatPrompt
model = OpenAICompletionsAIModel(api_key="your-api-key", model="gpt-4")
prompt = ChatPrompt(model, plugins=[mcp_client])
```

### MCP Server (Expose Tools)

```python
from microsoft.teams.apps import App
from microsoft.teams.mcpplugin import McpServerPlugin
from microsoft.teams.ai import Function
from pydantic import BaseModel

# Create MCP server plugin
mcp_server = McpServerPlugin(name="my-mcp-server")

# Define a tool
class EchoParams(BaseModel):
    input: str

async def echo_handler(params: EchoParams) -> str:
    return f"You said {params.input}"

# Register tool with MCP server
mcp_server.use_tool(
    Function(
        name="echo",
        description="Echo back whatever you said",
        parameter_schema=EchoParams,
        handler=echo_handler
    )
)

app = App(plugins=[mcp_server])
```
