"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from os import getenv

from dotenv import find_dotenv, load_dotenv
from microsoft.teams.ai import AgentWorkflow, ListMemory, UserMessage
from microsoft.teams.ai.function import Function
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext, App, AppOptions
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.openai_ai_model import OpenAIChatModel
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


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")

    openai_ai_model = OpenAIChatModel(
        client_or_key=AZURE_OPENAI_API_KEY,
        model=AZURE_OPENAI_MODEL,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    workflow = AgentWorkflow(openai_ai_model)

    def get_weather_handler(params: GetWeatherParams) -> str:
        return f"The weather in {params.location} is sunny"

    workflow.with_function(
        Function(
            name="get_weather",
            description="get weather from a particular location",
            parameter_schema=GetWeatherParams,
            handler=get_weather_handler,
        )
    )
    memory = ListMemory()
    workflow_result = await workflow.send(input=UserMessage(content=ctx.activity.text, role="user"), memory=memory)
    result = workflow_result.response
    if result.content:
        await ctx.reply(result.content)


if __name__ == "__main__":
    asyncio.run(app.start())
