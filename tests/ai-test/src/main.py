"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from os import getenv

from dotenv import find_dotenv, load_dotenv
from microsoft.teams.ai import Agent, Function, ListMemory, UserMessage
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext, App, AppOptions
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.openai import OpenAIModel
from pydantic import BaseModel

load_dotenv(find_dotenv(usecwd=True))


def get_required_env(key: str) -> str:
    value = getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


AZURE_OPENAI_API_KEY = get_required_env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = get_required_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_MODEL = get_required_env("AZURE_OPENAI_MODEL")
AZURE_OPENAI_API_VERSION = get_required_env("AZURE_OPENAI_API_VERSION")

app = App(AppOptions(plugins=[DevToolsPlugin()]))


class GetWeatherParams(BaseModel):
    location: str


openai_ai_model = OpenAIModel(
    client_or_key=AZURE_OPENAI_API_KEY,
    model=AZURE_OPENAI_MODEL,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)
memory = ListMemory()
agent = Agent(openai_ai_model, memory=memory)


def get_weather_handler(params: GetWeatherParams) -> str:
    return f"The weather in {params.location} is sunny"


agent.with_function(
    Function(
        name="get_weather",
        description="get weather from a particular location",
        parameter_schema=GetWeatherParams,
        handler=get_weather_handler,
    )
)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

    chat_result = await agent.send(
        input=UserMessage(content=ctx.activity.text, role="user"), on_chunk=lambda chunk: ctx.stream.emit(chunk)
    )
    result = chat_result.response
    if result.content:
        await ctx.reply(result.content)


if __name__ == "__main__":
    asyncio.run(app.start())
