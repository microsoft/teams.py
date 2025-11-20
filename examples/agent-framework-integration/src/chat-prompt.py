"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
from random import randint
from typing import Annotated, Literal

from microsoft.teams.ai import ChatPrompt, Function, ListMemory
from microsoft.teams.api import MessageActivity, MessageActivityInput
from microsoft.teams.apps import ActivityContext, App
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.mcpplugin import McpClientPlugin
from microsoft.teams.openai import OpenAICompletionsAIModel
from pydantic import BaseModel, Field

app = App(plugins=[DevToolsPlugin()])

# AI Model
model = OpenAICompletionsAIModel()


# Tool function definitions (same as agent-framework version)
class GetWeatherParams(BaseModel):
    location: Annotated[str, Field(description="The location to get the weather for.")]


def get_weather(params: GetWeatherParams) -> str:
    """Get the weather for a given location."""
    conditions = ["sunny", "cloudy", "rainy", "stormy"]
    return f"The weather in {params.location} is {conditions[randint(0, 3)]} with a high of {randint(10, 30)}°C."


class GetMenuSpecialsParams(BaseModel):
    """No parameters needed for menu specials"""

    pass


def get_menu_specials(params: GetMenuSpecialsParams) -> str:
    """Get today's menu specials."""
    return """
    Special Soup: Clam Chowder
    Special Salad: Cobb Salad
    Special Drink: Chai Tea
    """


@app.on_message_pattern(re.compile("basic .*"))
async def handle_basic_message(ctx: ActivityContext[MessageActivity]):
    """Handle message activities using ChatPrompt (equivalent to basic handler)."""
    ctx.logger.info("Handling basic message")
    text = ctx.activity.text.removeprefix("basic ")

    prompt = ChatPrompt(model)
    chat_result = await prompt.send(
        input=text,
        instructions="""
            You are a friendly but hilarious pirate robot.
            """,
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)


@app.on_message_pattern(re.compile("function .*"))
async def handle_tool_calling(ctx: ActivityContext[MessageActivity]):
    """Handle function calling using ChatPrompt with functions."""
    ctx.logger.info("Handling function calling message")
    text = ctx.activity.text.removeprefix("function ")

    prompt = ChatPrompt(model)
    prompt.with_function(
        Function(
            name="get_weather",
            description="Get the weather for a given location.",
            parameter_schema=GetWeatherParams,
            handler=get_weather,
        )
    ).with_function(
        Function(
            name="get_menu_specials",
            description="Get today's menu specials.",
            parameter_schema=GetMenuSpecialsParams,
            handler=get_menu_specials,
        )
    )

    chat_result = await prompt.send(
        input=text,
        instructions="""
            You are a friendly but hilarious pirate robot.
            You MUST use a tool call to answer the user's question.
            If no tool call is available, then you may tell the user that
            they need to use one of the available functions.
            """,
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)


@app.on_message_pattern(re.compile("streaming .*"))
async def handle_streaming(ctx: ActivityContext[MessageActivity]):
    """Handle streaming responses using ChatPrompt with on_chunk callback."""
    ctx.logger.info("Handling streaming message")
    text = ctx.activity.text.removeprefix("streaming ")

    prompt = ChatPrompt(model)
    prompt.with_function(
        Function(
            name="get_weather",
            description="Get the weather for a given location.",
            parameter_schema=GetWeatherParams,
            handler=get_weather,
        )
    ).with_function(
        Function(
            name="get_menu_specials",
            description="Get today's menu specials.",
            parameter_schema=GetMenuSpecialsParams,
            handler=get_menu_specials,
        )
    )

    chat_result = await prompt.send(
        input=text,
        instructions="""
            You are a friendly but hilarious pirate robot.
            """,
        on_chunk=lambda chunk: ctx.stream.emit(chunk),
    )

    # Emit final AI generated marker for streaming
    if chat_result.response.content:
        ctx.stream.emit(MessageActivityInput().add_ai_generated())


class SentimentResult(BaseModel):
    sentiment: Literal["positive", "negative"]


@app.on_message_pattern(re.compile("structured .*"))
async def handle_structured_message(ctx: ActivityContext[MessageActivity]):
    """
    Handle structured output requests.

    NOTE: ChatPrompt does not currently support structured output (response_format).
    This handler uses instructions to request structured format as a workaround.
    """
    ctx.logger.info("Handling structured message")
    text = ctx.activity.text.removeprefix("structured ")

    prompt = ChatPrompt(model)
    chat_result = await prompt.send(
        input=text,
        instructions="""
            You are an agent that judges if a sentence is positive or negative.
            Respond with ONLY a JSON object in this format: {"sentiment": "positive"} or {"sentiment": "negative"}
            Do not include any other text.
            """,
    )

    if chat_result.response.content:
        # Note: Without response_format support, we get a string response
        # In a production app, you would parse the JSON string here
        await ctx.reply(chat_result.response.content)


# Memory store for conversations
memory_store: dict[str, ListMemory] = {}


def get_or_create_memory(conversation_id: str) -> ListMemory:
    """Get or create conversation memory for a specific conversation."""
    if conversation_id not in memory_store:
        memory_store[conversation_id] = ListMemory()
    return memory_store[conversation_id]


@app.on_message_pattern(re.compile("memory .*"))
async def handle_memory_message(ctx: ActivityContext[MessageActivity]):
    """Handle messages with conversation memory using ChatPrompt with ListMemory."""
    ctx.logger.info("Handling memory message")
    text = ctx.activity.text.removeprefix("memory ")

    # Get or create memory for this conversation
    memory = get_or_create_memory(ctx.activity.conversation.id)

    prompt = ChatPrompt(model, memory=memory)
    chat_result = await prompt.send(
        input=text,
        instructions="""
            You are a friendly but hilarious pirate robot.
            """,
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)


@app.on_message_pattern(re.compile("mcp .*"))
async def handle_mcp_message(ctx: ActivityContext[MessageActivity]):
    """Handle MCP requests using ChatPrompt with McpClientPlugin."""
    ctx.logger.info("Handling mcp message")
    text = ctx.activity.text.removeprefix("mcp ")

    # Create MCP plugin for Microsoft Learn
    mcp_plugin = McpClientPlugin()
    mcp_plugin.use_mcp_server("https://learn.microsoft.com/api/mcp")

    # Get or create memory for this conversation
    memory = get_or_create_memory(ctx.activity.conversation.id)

    prompt = ChatPrompt(model, memory=memory, plugins=[mcp_plugin])
    chat_result = await prompt.send(
        input=text,
        instructions="""
            You MUST use the tools that you have available to answer the user's request
            """,
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)


@app.on_message
async def handle_message2(ctx: ActivityContext[MessageActivity]):
    ctx.logger.info("Handling all message")


if __name__ == "__main__":
    asyncio.run(app.start())
