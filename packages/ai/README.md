# Microsoft Teams AI

<p>
    <a href="https://pypi.org/project/microsoft-teams-ai/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-ai" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-ai/" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-ai" />
    </a>
</p>

AI-powered conversational experiences for Microsoft Teams applications.
Provides prompt management, action planning, and model integration for building intelligent Teams bots.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Installation

```bash
uv add microsoft-teams-ai
```

## Usage

```python
from microsoft.teams.ai import Agent
from microsoft.teams.openai import OpenAICompletionsAIModel

model = OpenAICompletionsAIModel(api_key="your-api-key", model="gpt-4")
agent = Agent(model=model)

result = await agent.send(
    input="Hello!",
    instructions="You are a helpful assistant."
)
```