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
Enables Teams bots to use MCP servers as tools and resources.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Features

- **MCP Server Integration**: Connect to MCP servers for extended capabilities
- **Tool Execution**: Execute MCP tools from within Teams conversations
- **Resource Access**: Access MCP resources in your bot logic
- **FastMCP Support**: Compatible with FastMCP server implementations

## Installation

```bash
# Using uv (recommended)
uv add microsoft-teams-mcpplugin

# Using pip
pip install microsoft-teams-mcpplugin
```

## Quick Start

```python
from microsoft.teams.apps import App
from microsoft.teams.mcpplugin import McpClientPlugin

app = App()

# Configure MCP client plugin
mcp_plugin = McpClientPlugin(
    server_command="uvx",
    server_args=["mcp-server-time"]
)

# Register the plugin
app.use(mcp_plugin)

# MCP tools are now available to your AI agent
```

## Using MCP Resources

```python
# Access MCP resources through the plugin
# The plugin integrates with your Teams AI agent
# and makes MCP tools available as functions

# MCP tools can be called by the AI model
# when using the Teams AI framework
```

## Supported MCP Servers

This plugin works with any MCP-compliant server, including:
- Built-in MCP servers (filesystem, git, etc.)
- Custom MCP servers
- FastMCP-based servers
