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
from microsoft.teams.openai import OpenAICompletionsAIModel
from microsoft.teams.ai import ChatPrompt

# Configure OpenAI model
model = OpenAICompletionsAIModel(
    api_key="your-api-key",
    model="gpt-4",
    temperature=0.7
)

# Use with Teams AI
prompt = ChatPrompt(instructions="You are a helpful assistant.")
result = await model.chat(prompt)
```

## Azure OpenAI Support

```python
from microsoft.teams.openai import OpenAICompletionsAIModel

# Configure Azure OpenAI
model = OpenAICompletionsAIModel(
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment-name",
    model="gpt-4"
)
```

## Streaming Responses

```python
# Enable streaming for real-time responses
model = OpenAIResponsesAIModel(
    api_key="your-api-key",
    model="gpt-4"
)

# Streaming is handled through the model's chat method
result = await model.chat(prompt, stream=True)
```

## Function Calling

```python
from microsoft.teams.ai import Function

# Define functions for the model to call
get_weather = Function(
    name="get_weather",
    description="Get the weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        },
        "required": ["location"]
    }
)

# Add functions to your prompt
prompt = ChatPrompt(
    instructions="You are a helpful assistant.",
    functions=[get_weather]
)

model = OpenAICompletionsAIModel(
    api_key="your-api-key",
    model="gpt-4"
)
```