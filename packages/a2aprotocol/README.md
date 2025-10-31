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

## Installation

```bash
uv add microsoft-teams-a2a
```

## Usage

```python
from microsoft.teams.apps import App
from microsoft.teams.a2a import A2APlugin, A2APluginOptions
from a2a.types import AgentCard

app = App()

agent_card = AgentCard(
    name="My Agent",
    description="A helpful agent",
    capabilities={}
)

a2a_plugin = A2APlugin(A2APluginOptions(agent_card=agent_card))
app.use(a2a_plugin)
```
