# Microsoft Teams A2A Protocol

<p>
    <a href="https://pypi.org/project/microsoft-teams-a2a/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-a2a" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-a2a" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-a2a" />
    </a>
</p>

Agent-to-Agent (A2A) protocol support for Microsoft Teams AI applications.
Enables Teams agents to communicate and collaborate with other AI agents using standardized protocols.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Features

- **Agent Communication**: Enable Teams agents to communicate with other A2A-compatible agents
- **HTTP Server Support**: Built-in HTTP server for A2A protocol endpoints
- **Prompt Integration**: Seamless integration with Teams AI prompt system
- **Standardized Protocol**: Uses the A2A SDK for standard agent communication

## Installation

```bash
# Using uv (recommended)
uv add microsoft-teams-a2a

# Using pip
pip install microsoft-teams-a2a
```

## Quick Start

```python
from microsoft.teams.apps import App
from microsoft.teams.a2a import A2APlugin, A2APluginOptions
from a2a.types import AgentCard

app = App()

# Configure A2A plugin with agent card
agent_card = AgentCard(
    name="My Agent",
    description="A helpful agent",
    capabilities={}
)

a2a_plugin = A2APlugin(
    A2APluginOptions(agent_card=agent_card)
)

# Register the plugin with your app
app.use(a2a_plugin)

# Your Teams agent is now accessible via A2A protocol
```

## Agent Integration

```python
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext

# Define message handler for both Teams and A2A requests
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.send(f"Received: {ctx.activity.text}")
```

## Use Cases

- Multi-agent collaboration systems
- Agent orchestration and delegation
- Cross-platform agent communication
- Distributed AI workflows
