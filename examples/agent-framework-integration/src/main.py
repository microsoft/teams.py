"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
from random import randint
from typing import Annotated, Literal

from agent_framework import ChatAgent, ChatMessageStore, MCPStreamableHTTPTool
from agent_framework.azure import AzureOpenAIChatClient
from microsoft.teams.api import MessageActivity
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.devtools import DevToolsPlugin
from pydantic import BaseModel, Field

app = App(plugins=[DevToolsPlugin()])


def get_weather(
    location: Annotated[str, Field(description="The location to get the weather for.")],
) -> str:
    """Get the weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    return f"The weather in {location} is {conditions[randint(0, 3)]} with a high of {randint(10, 30)}°C."


def get_menu_specials() -> str:
    """Get today's menu specials."""
    return """
    Special Soup: Clam Chowder
    Special Salad: Cobb Salad
    Special Drink: Chai Tea
    """


@app.on_message_pattern(re.compile("basic .*"))
async def handle_basic_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using the new generated handler system."""
    ctx.logger.info("Handling basic message")
    text = ctx.activity.text.removeprefix("basic ")
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(),
        instructions="""
            You are a friendly but hilarious pirate robot.
            """,
    )

    result = await agent.run(text)
    await ctx.reply(result.text)


@app.on_message_pattern(re.compile("function .*"))
async def handle_tool_calling(ctx: ActivityContext[MessageActivity]):
    ctx.logger.info("Handling function calling message")
    text = ctx.activity.text.removeprefix("function ")
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(),
        instructions="""
            You are a friendly but hilarious pirate robot.
            You MUST use a tool call to answer the user's question.
            If no tool call is available, then you may tell the user that
            they need to use one of the available functions.
            """,
        tools=[get_weather, get_menu_specials],
    )

    result = await agent.run(text)
    await ctx.reply(result.text)


@app.on_message_pattern(re.compile("streaming .*"))
async def handle_streaming(ctx: ActivityContext[MessageActivity]):
    ctx.logger.info("Handling streaming message")
    text = ctx.activity.text.removeprefix("streaming ")
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(),
        instructions="""
            You are a friendly but hilarious pirate robot.
            """,
        tools=[get_weather, get_menu_specials],
    )

    async for update in agent.run_stream(text):
        ctx.stream.emit(update.text)


class SentimentResult(BaseModel):
    sentiment: Literal["positive", "negative"]


@app.on_message_pattern(re.compile("structured .*"))
async def handle_structured_message(ctx: ActivityContext[MessageActivity]):
    ctx.logger.info("Handling structured message")
    text = ctx.activity.text.removeprefix("structured ")
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(),
        instructions="""
            You are an agent that judges if a senstence is positive or negative.
            """,
    )

    result = await agent.run(text, response_format=SentimentResult)

    if result.value:
        await ctx.reply(str(result.value))


memory = ChatMessageStore()


@app.on_message_pattern(re.compile("memory .*"))
async def handle_memory_message(ctx: ActivityContext[MessageActivity]):
    ctx.logger.info("Handling memory message")
    text = ctx.activity.text.removeprefix("memory ")
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(),
        instructions="""
            You are a friendly but hilarious pirate robot.
            """,
        chat_message_store_factory=lambda: memory,
    )

    result = await agent.run(text)
    await ctx.reply(result.text)


@app.on_message_pattern(re.compile("mcp .*"))
async def handle_mcp_message(ctx: ActivityContext[MessageActivity]):
    ctx.logger.info("Handling mcp message")
    text = ctx.activity.text.removeprefix("mcp ")
    learn_mcp = MCPStreamableHTTPTool("microsoft-learn", "https://learn.microsoft.com/api/mcp")
    agent = ChatAgent(
        chat_client=AzureOpenAIChatClient(),
        instructions="""
            You MUST use the tools that you have available to answer the user's request
            """,
        chat_message_store_factory=lambda: memory,
        tools=[learn_mcp],
    )

    result = await agent.run(text)
    await ctx.reply(result.text)


if __name__ == "__main__":
    asyncio.run(app.start())
