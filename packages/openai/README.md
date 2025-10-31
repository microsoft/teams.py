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

## Features

- **Chat Completions**: GPT-3.5, GPT-4, and compatible models
- **Streaming Support**: Real-time response streaming
- **Function Calling**: Native support for OpenAI function calling
- **OpenAI-Compatible APIs**: Works with Azure OpenAI, LM Studio, and other compatible services

## Installation

```bash
# Using uv (recommended)
uv add microsoft-teams-openai

# Using pip
pip install microsoft-teams-openai
```

## Quick Start

```python
from microsoft.teams.openai import OpenAIModel
from microsoft.teams.ai import PromptManager

# Configure OpenAI model
model = OpenAIModel(
    api_key="your-api-key",
    model="gpt-4",
    temperature=0.7
)

# Use with Teams AI
prompt_manager = PromptManager()
result = await model.complete(prompt_manager, "Hello!")
```

## Azure OpenAI Support

```python
from microsoft.teams.openai import AzureOpenAIModel

# Configure Azure OpenAI
model = AzureOpenAIModel(
    api_key="your-azure-key",
    endpoint="https://your-resource.openai.azure.com/",
    deployment="your-deployment-name",
    api_version="2024-02-01"
)
```

## Streaming Responses

```python
# Enable streaming for real-time responses
model = OpenAIModel(
    api_key="your-api-key",
    model="gpt-4",
    stream=True
)

async for chunk in model.stream_complete(prompt_manager, "Tell me a story"):
    print(chunk.content, end="", flush=True)
```

## Function Calling

```python
# Define functions for the model to call
functions = [
    {
        "name": "get_weather",
        "description": "Get the weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string"}
            }
        }
    }
]

model = OpenAIModel(
    api_key="your-api-key",
    model="gpt-4",
    functions=functions
)
```