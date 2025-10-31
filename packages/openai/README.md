# Microsoft Teams OpenAI

<p>
    <a href="https://pypi.org/project/microsoft-teams-openai/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-openai" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-openai" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-openai" />
    </a>
</p>

OpenAI model implementations for Microsoft Teams AI applications.
Supports OpenAI and OpenAI-compatible APIs for chat completions and embeddings.

<a href="https://microsoft.github.io/teams-ai" target="_blank">
    <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
</a>

## Installation

```bash
uv add microsoft-teams-openai
```

## Usage

```python
from microsoft.teams.openai import OpenAICompletionsAIModel
from microsoft.teams.ai import Agent

model = OpenAICompletionsAIModel(api_key="your-api-key", model="gpt-4")
agent = Agent(model=model)
```