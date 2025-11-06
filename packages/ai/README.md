# Microsoft Teams SDK

<p>
    <a href="https://pypi.org/project/microsoft-teams-ai/" target="_blank">
        <img src="https://img.shields.io/pypi/v/microsoft-teams-ai" />
    </a>
    <a href="https://pypi.org/project/microsoft-teams-ai/" target="_blank">
        <img src="https://img.shields.io/pypi/dw/microsoft-teams-ai" />
    </a>
    <a href="https://microsoft.github.io/teams-sdk" target="_blank">
        <img src="https://img.shields.io/badge/📖 Getting Started-blue?style=for-the-badge" />
    </a>
</p>

AI-powered conversational experiences for Microsoft Teams applications.
Provides prompt management, action planning, and model integration for building intelligent Teams bots.

[📖 Documentation](https://microsoft.github.io/teams-sdk/python/in-depth-guides/ai/)

## Installation

```bash
uv add microsoft-teams-ai
```

## Usage

### ChatPrompt

```python
from microsoft.teams.ai import ChatPrompt, Function
from microsoft.teams.openai import OpenAICompletionsAIModel
from pydantic import BaseModel

model = OpenAICompletionsAIModel(api_key="your-api-key", model="gpt-4")

# Create a ChatPrompt
prompt = ChatPrompt(model)

result = await prompt.send(
    input="Hello!",
    instructions="You are a helpful assistant."
)
```

### Function Calling

```python
class GetWeatherParams(BaseModel):
    location: str

async def get_weather(params: GetWeatherParams) -> str:
    return f"The weather in {params.location} is sunny"

weather_function = Function(
    name="get_weather",
    description="Get weather for a location",
    parameter_schema=GetWeatherParams,
    handler=get_weather
)

prompt = ChatPrompt(model, functions=[weather_function])
```
