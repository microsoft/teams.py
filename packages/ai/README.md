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
from microsoft.teams.ai import Agent, ChatPrompt
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
    response = await agent.run(ctx)
    await ctx.send(response)
```

## Prompt Templates

```python
# Define a chat prompt
prompt = ChatPrompt(
    instructions="You are a helpful assistant for {{company}}.",
    functions=[]
)

# Use the prompt with variables
result = await agent.chat(
    prompt,
    variables={"company": "Contoso"}
)
```

## Actions and Tools

```python
from microsoft.teams.ai import Function

# Register custom functions
weather_function = Function(
    name="get_weather",
    description="Get weather for a location",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        }
    }
)

# Add function handler
@agent.function("get_weather")
async def get_weather(location: str):
    # Fetch weather data
    return {"temperature": 72, "conditions": "sunny"}
```

## Memory and State

```python
# Configure memory for conversation history
from microsoft.teams.ai import ListMemory

memory = ListMemory(max_items=10)
agent = Agent(
    model=model,
    memory=memory
)

# Access conversation state
messages = await memory.get()
await memory.add(user_message)
```