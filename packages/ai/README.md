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
from microsoft.teams.ai import AIAgent, PromptManager
from microsoft.teams.openai import OpenAIModel

# Create prompt manager
prompts = PromptManager()

# Configure AI model
model = OpenAIModel(
    api_key="your-api-key",
    model="gpt-4"
)

# Create AI agent
agent = AIAgent(
    model=model,
    prompts=prompts
)

# Use in Teams app
@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    response = await agent.run(ctx)
    await ctx.send(response)
```

## Prompt Templates

```python
# Define a prompt template
prompts.add_prompt("greeting", """
You are a helpful assistant for {{company}}.
Greet the user and ask how you can help them today.
""")

# Use the prompt with variables
result = await agent.run(
    ctx,
    prompt_name="greeting",
    variables={"company": "Contoso"}
)
```

## Actions and Tools

```python
from microsoft.teams.ai import Action

# Register custom actions
@agent.action("get_weather")
async def get_weather(context, parameters):
    location = parameters.get("location")
    # Fetch weather data
    return {"temperature": 72, "conditions": "sunny"}

# AI can now call this action when needed
```

## Memory and State

```python
# Configure memory for conversation history
from microsoft.teams.ai import ConversationMemory

memory = ConversationMemory(max_turns=10)
agent = AIAgent(
    model=model,
    prompts=prompts,
    memory=memory
)

# Access conversation state
state = await memory.get_state(ctx)
state["user_preference"] = "dark_mode"
await memory.save_state(ctx, state)
```