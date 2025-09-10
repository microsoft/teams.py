"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from os import getenv

from dotenv import find_dotenv, load_dotenv
from microsoft.teams.ai import Agent, ListMemory
from microsoft.teams.api import MessageActivity, TypingActivityInput
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.mcpplugin import McpClientPlugin
from microsoft.teams.openai import OpenAIResponsesAIModel

app = App(plugins=[DevToolsPlugin()])
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

responses_openai_ai_model = OpenAIResponsesAIModel(
    key=AZURE_OPENAI_API_KEY,
    model=AZURE_OPENAI_MODEL,
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_version=AZURE_OPENAI_API_VERSION,
    stateful=True,
)
chat_memory = ListMemory()
mcp_plugin = McpClientPlugin()
mcp_plugin.use_mcp_server("https://learn.microsoft.com/api/mcp")

responses_agent = Agent(responses_openai_ai_model, memory=chat_memory, plugins=[mcp_plugin])


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    print(f"[GENERATED onMessage] Message received: {ctx.activity.text}")
    print(f"[GENERATED onMessage] From: {ctx.activity.from_}")
    await ctx.send(TypingActivityInput())

    result = await responses_agent.send(ctx.activity.text)
    if result.response.content:
        await ctx.reply(result.response.content)


if __name__ == "__main__":
    asyncio.run(app.start())
