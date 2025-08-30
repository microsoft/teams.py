"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
from os import getenv

from dotenv import find_dotenv, load_dotenv
from microsoft.teams.ai import Agent, Function, ListMemory, UserMessage
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext, App, AppOptions
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.openai import OpenAICompletionsAIModel, OpenAIResponsesAIModel
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

# Global state for mode switching
current_mode = "responses"  # "chat" or "responses"


class GetWeatherParams(BaseModel):
    location: str


chat_openai_ai_model = OpenAICompletionsAIModel(
    key=AZURE_OPENAI_API_KEY,
    model=AZURE_OPENAI_MODEL,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
)

responses_openai_ai_model = OpenAIResponsesAIModel(
    client_or_key=AZURE_OPENAI_API_KEY,
    model=AZURE_OPENAI_MODEL,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
    stateful=True,
)
chat_memory = ListMemory()

chat_agent = Agent(chat_openai_ai_model)
responses_agent = Agent(responses_openai_ai_model)


def get_weather_handler(params: GetWeatherParams) -> str:
    return f"The weather in {params.location} is sunny"


for agent in [chat_agent, responses_agent]:
    agent.with_function(
        Function(
            name="get_weather",
            description="get weather from a particular location",
            parameter_schema=GetWeatherParams,
            handler=get_weather_handler,
        )
    )


@app.on_message_pattern(re.compile(r"^mode\b"))
async def handle_mode_switch(ctx: ActivityContext[MessageActivity]):
    """Handle mode switching between chat and responses API."""
    global current_mode

    text = ctx.activity.text.lower().strip()

    if "chat" in text:
        current_mode = "chat"
        await ctx.reply("🔄 Switched to **Chat Completions** mode")
    elif "responses" in text:
        current_mode = "responses"
        await ctx.reply("🔄 Switched to **Responses API** mode")
    else:
        await ctx.reply(f"📋 Current mode: **{current_mode}**")


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    global current_mode

    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")
    print(f"[GENERATED onMessage] Mode: {current_mode}")

    # Create AI model based on current mode
    if current_mode == "responses":
        agent = responses_agent
    else:  # chat mode
        agent = chat_agent

    chat_result = await agent.send(
        input=UserMessage(content=ctx.activity.text, role="user"), on_chunk=lambda chunk: ctx.stream.emit(chunk)
    )
    result = chat_result.response
    if result.content:
        await ctx.reply(result.content)
    else:
        print("No response!")


if __name__ == "__main__":
    asyncio.run(app.start())
