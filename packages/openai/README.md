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

# Configure OpenAI model
model = OpenAICompletionsAIModel(
    api_key="your-api-key",
    model="gpt-4",
    temperature=0.7
)

# Use with Teams AI Agent
from microsoft.teams.ai import Agent

agent = Agent(model=model)
result = await agent.send(
    input="Hello!",
    instructions="You are a helpful assistant."
)
```

## Azure OpenAI Support

```python
from microsoft.teams.openai import OpenAICompletionsAIModel

# Configure Azure OpenAI with base_url
model = OpenAICompletionsAIModel(
    api_key="your-azure-key",
    base_url="https://your-resource.openai.azure.com/openai/deployments/your-deployment-name",
    model="gpt-4"
)
```

## Streaming Responses

```python
from microsoft.teams.openai import OpenAIResponsesAIModel
from microsoft.teams.ai import UserMessage

# Use OpenAIResponsesAIModel for streaming support
model = OpenAIResponsesAIModel(
    api_key="your-api-key",
    model="gpt-4"
)

# Streaming is handled through callback
def on_chunk(chunk: str):
    print(chunk, end="", flush=True)

result = await model.generate_text(
    input=UserMessage(content="Tell me a story"),
    on_chunk=on_chunk
)
```

## Function Calling

```python
from microsoft.teams.ai import Agent, Function
from pydantic import BaseModel

class GetWeatherParams(BaseModel):
    location: str

async def get_weather_handler(params: GetWeatherParams) -> str:
    return f"Weather in {params.location}: sunny, 72°F"

# Configure agent with function
model = OpenAICompletionsAIModel(
    api_key="your-api-key",
    model="gpt-4"
)

agent = Agent(model=model)
agent.with_function(
    Function(
        name="get_weather",
        description="Get the weather for a location",
        parameter_schema=GetWeatherParams,
        handler=get_weather_handler
    )
)
```