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

## Features

- **Prompt Management**: Template-based prompt system with variable substitution
- **Action Planning**: AI-driven action execution with validation
- **Model Integration**: Compatible with OpenAI, Azure OpenAI, and custom models
- **Memory Management**: Conversation history and state management
- **Function Calling**: Structured actions and tool use

## Installation

```bash
# Using uv (recommended)
uv add microsoft-teams-ai

# Using pip
pip install microsoft-teams-ai
```

## Quick Start

```python
from microsoft.teams.ai import Agent
from microsoft.teams.openai import OpenAICompletionsAIModel

# Create AI model
model = OpenAICompletionsAIModel(
    api_key="your-api-key",
    model="gpt-4"
)

# Create agent
agent = Agent(model=model)

# Use in Teams app
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    result = await agent.send(
        input=ctx.activity.text,
        instructions="You are a helpful assistant."
    )
    await ctx.send(result.response.content)
```

## Prompt Instructions

```python
# Define custom instructions for your agent
result = await agent.send(
    input="What can you help me with?",
    instructions="You are a helpful assistant for {{company}}. Be professional and courteous."
)
```

## Function Calling

```python
from microsoft.teams.ai import Function
from pydantic import BaseModel

class GetWeatherParams(BaseModel):
    location: str

async def get_weather_handler(params: GetWeatherParams) -> str:
    # Fetch weather data
    return f"Weather in {params.location}: sunny, 72°F"

# Register function with agent
agent.with_function(
    Function(
        name="get_weather",
        description="Get weather for a location",
        parameter_schema=GetWeatherParams,
        handler=get_weather_handler
    )
)
```

## Memory Management

```python
from microsoft.teams.ai import ListMemory, UserMessage

# Create memory for conversation history
memory = ListMemory()

# Add messages to memory
await memory.push(UserMessage(content="Hello"))

# Retrieve conversation history
messages = await memory.get_all()
```