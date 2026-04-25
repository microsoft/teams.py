# Microsoft Teams OpenAI

> [!WARNING]
> **Deprecated** — This package was originally in preview, but we have decided to stop maintaining it before General Availability. We recommend using the official [OpenAI Python SDK](https://github.com/openai/openai-python) instead, which provides better long-term support for OpenAI integrations.

<p>
    <a href="https://pypi.org/project/microsoft-teams-openai/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-openai" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-openai" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-openai" />
    </a>
    <a href="https://microsoft.github.io/teams-sdk" target="_blank">
        <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
    </a>
</p>


OpenAI model implementations for Microsoft Teams AI applications.
Supports OpenAI and OpenAI-compatible APIs for chat completions and embeddings.

## Installation

```bash
pip install microsoft-teams-openai
```

Or if using uv:

```bash
uv add microsoft-teams-openai
```

## Usage

```python
from microsoft_teams.openai import OpenAICompletionsAIModel
from microsoft_teams.ai import ChatPrompt

model = OpenAICompletionsAIModel(api_key="your-api-key", model="gpt-4")
prompt = ChatPrompt(model)
```
