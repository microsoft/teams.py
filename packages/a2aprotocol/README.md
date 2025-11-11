# Microsoft Teams A2A

<p>
    <a href="https://pypi.org/project/microsoft-teams-a2a/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-a2a" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-a2a" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-a2a" />
    </a>
    <a href="https://microsoft.github.io/teams-sdk" target="_blank">
        <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
    </a>
</p>

Agent-to-Agent (A2A) protocol support for Microsoft Teams AI applications.
Enables Teams agents to communicate and collaborate with other AI agents using standardized protocols.

## Installation

```bash
uv add microsoft-teams-a2a
```

## Usage

### A2A Server (Expose Agent)

```python
from microsoft.teams.apps import App
from microsoft.teams.a2a import A2APlugin, A2APluginOptions
from a2a.types import AgentCard, AgentCapabilities

app = App()

# Define agent card with capabilities
agent_card = AgentCard(
    name="weather_agent",
    description="An agent that can tell you the weather",
    url="http://localhost:4000/a2a/",
    version="0.0.1",
    protocol_version="0.3.0",
    capabilities=AgentCapabilities(),
    default_input_modes=[],
    default_output_modes=[]
)

a2a_server = A2APlugin(A2APluginOptions(agent_card=agent_card))
app = App(plugins=[a2a_server])
```

### A2A Client (Use Other Agents)

```python
from microsoft.teams.a2a import A2AClientPlugin, A2APluginUseParams
from microsoft.teams.ai import ChatPrompt
from microsoft.teams.openai import OpenAICompletionsAIModel

model = OpenAICompletionsAIModel(api_key="your-api-key", model="gpt-4")

# Connect to another A2A agent
a2a_client = A2AClientPlugin()
a2a_client.on_use_plugin(
    A2APluginUseParams(
        key="my-weather-agent",
        base_url="http://localhost:4000/a2a",
        card_url=".well-known/agent-card.json"
    )
)

prompt = ChatPrompt(model, plugins=[a2a_client])
```
