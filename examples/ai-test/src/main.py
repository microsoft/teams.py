"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
from os import getenv

from dotenv import find_dotenv, load_dotenv
from handlers import (
    LoggingAIPlugin,
    handle_citations_demo,
    handle_multiple_functions,
    handle_pokemon_search,
    handle_stateful_conversation,
)
from handlers.feedback_management import (
    get_feedback_summary,
    handle_feedback_submission,
    initialize_feedback_storage,
)
from handlers.memory_management import clear_conversation_memory
from microsoft_teams.ai import ChatPrompt
from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.api.activities.invoke.message.submit_action import MessageSubmitActionInvokeActivity
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.devtools import DevToolsPlugin
from microsoft_teams.openai import OpenAICompletionsAIModel, OpenAIResponsesAIModel

load_dotenv(find_dotenv(usecwd=True))


def get_required_env(key: str) -> str:
    value = getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


AZURE_OPENAI_MODEL = get_required_env("AZURE_OPENAI_MODEL")

# Global plugin instance for tracking
plugin_instance = LoggingAIPlugin()

app = App(plugins=[DevToolsPlugin()])

# Models for different AI approaches
completions_model = OpenAICompletionsAIModel(
    model=AZURE_OPENAI_MODEL,
)

responses_model = OpenAIResponsesAIModel(
    model=AZURE_OPENAI_MODEL,
    stateful=True,
)

# Global state
current_model = completions_model


# Simple chat handler (like TypeScript "hi" example)
@app.on_message_pattern(re.compile(r"^hi$", re.IGNORECASE))
async def handle_simple_chat(ctx: ActivityContext[MessageActivity]):
    """Handle 'hi' message with simple AI response"""
    prompt = ChatPrompt(completions_model)
    chat_result = await prompt.send(
        input=ctx.activity.text, instructions="You are a friendly assistant who talks like a pirate"
    )

    if chat_result.response.content:
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
        await ctx.send(message)


# Command handlers (like TypeScript command pattern)
@app.on_message_pattern(re.compile(r"^pokemon\s+(.+)", re.IGNORECASE))
async def handle_pokemon_command(ctx: ActivityContext[MessageActivity]):
    """Handle 'pokemon <name>' command"""
    match = re.match(r"^pokemon\s+(.+)", ctx.activity.text, re.IGNORECASE)
    if match:
        pokemon_name = match.group(1).strip()
        ctx.activity.text = pokemon_name  # Update activity text for handler
        await handle_pokemon_search(current_model, ctx)


@app.on_message_pattern(re.compile(r"^weather\b", re.IGNORECASE))
async def handle_weather_command(ctx: ActivityContext[MessageActivity]):
    """Handle 'weather' command with multiple functions"""
    await handle_multiple_functions(current_model, ctx)


# Streaming handler (like TypeScript streaming example)
@app.on_message_pattern(re.compile(r"^stream\s+(.+)", re.IGNORECASE))
async def handle_streaming(ctx: ActivityContext[MessageActivity]):
    """Handle 'stream <query>' command"""
    match = re.match(r"^stream\s+(.+)", ctx.activity.text, re.IGNORECASE)
    if match:
        query = match.group(1).strip()

        prompt = ChatPrompt(current_model)
        chat_result = await prompt.send(
            input=query,
            instructions="You are a friendly assistant who responds in extremely verbose language",
            on_chunk=lambda chunk: ctx.stream.emit(chunk) if hasattr(ctx, "stream") else None,
        )

        if hasattr(ctx.activity.conversation, "is_group") and ctx.activity.conversation.is_group:
            # Group chat - send final response
            if chat_result.response.content:
                message = MessageActivityInput(text=chat_result.response.content).add_ai_generated()
                await ctx.send(message)
        else:
            # 1:1 chat - streaming handled above
            if hasattr(ctx, "stream"):
                ctx.stream.emit(MessageActivityInput().add_ai_generated())


# Utility commands
@app.on_message_pattern(re.compile(r"^citations?\b", re.IGNORECASE))
async def handle_citations_command(ctx: ActivityContext[MessageActivity]):
    """Handle 'citations' command"""
    await handle_citations_demo(ctx)


@app.on_message_pattern(re.compile(r"^model\s*(.*)$", re.IGNORECASE))
async def handle_model_switch(ctx: ActivityContext[MessageActivity]):
    """Handle model switching"""
    global current_model

    match = re.match(r"^model\s*(.*)$", ctx.activity.text, re.IGNORECASE)
    if match:
        model_name = match.group(1).strip().lower()
        if "completion" in model_name:
            current_model = completions_model
            await ctx.reply("🔄 Switched to **Chat Completions** model")
        elif "response" in model_name:
            current_model = responses_model
            await ctx.reply("🔄 Switched to **Responses API** model")
        else:
            await ctx.reply(
                f"📋 Current model: **{'completions' if current_model == completions_model else 'responses'}**"
            )


@app.on_message_pattern(re.compile(r"^plugin\b", re.IGNORECASE))
async def handle_plugin_stats(ctx: ActivityContext[MessageActivity]):
    """Handle 'plugin stats' command"""
    await ctx.reply(
        f"🔌 Plugin function calls so far: {', '.join(plugin_instance.function_calls) if plugin_instance.function_calls else 'None'}"  # noqa E501
    )


@app.on_message_pattern(re.compile(r"^memory\s+clear\b", re.IGNORECASE))
async def handle_memory_clear(ctx: ActivityContext[MessageActivity]):
    """Handle 'memory clear' command"""
    await clear_conversation_memory(ctx.activity.conversation.id)
    await ctx.reply("🧠 Memory cleared!")


# Feedback demonstration
@app.on_message_pattern(re.compile(r"^feedback\s+demo\b", re.IGNORECASE))
async def handle_feedback_demo(ctx: ActivityContext[MessageActivity]):
    """Handle 'feedback demo' command to demonstrate feedback collection"""
    prompt = ChatPrompt(current_model)
    chat_result = await prompt.send(
        input="Tell me a short joke", instructions="You are a comedian. Keep responses brief and funny."
    )

    if chat_result.response.content:
        # Create message with feedback enabled and initialize storage
        message = MessageActivityInput(text=chat_result.response.content).add_ai_generated().add_feedback()
        sent_message = await ctx.send(message)

        # Initialize feedback storage for this message
        if sent_message and hasattr(sent_message, "id"):
            initialize_feedback_storage(sent_message.id)
            await ctx.reply(f"💡 Feedback enabled! Try reacting or providing feedback. Message ID: {sent_message.id}")


@app.on_message_pattern(re.compile(r"^feedback\s+stats\s+(.+)", re.IGNORECASE))
async def handle_feedback_stats(ctx: ActivityContext[MessageActivity]):
    """Handle 'feedback stats <message_id>' command"""
    match = re.match(r"^feedback\s+stats\s+(.+)", ctx.activity.text, re.IGNORECASE)
    if match:
        message_id = match.group(1).strip()
        summary = get_feedback_summary(message_id)
        await ctx.reply(f"📊 Feedback for message {message_id}: {summary}")


# Handle feedback submission events (like TypeScript message.submit.feedback)
@app.on_message_submit_feedback
async def handle_message_feedback(ctx: ActivityContext[MessageSubmitActionInvokeActivity]):
    """Handle feedback submission events"""
    await handle_feedback_submission(ctx)


# Fallback stateful conversation handler (like TypeScript fallback)
@app.on_message
async def handle_fallback(ctx: ActivityContext[MessageActivity]):
    """Fallback handler for stateful conversation"""
    await handle_stateful_conversation(current_model, ctx)


if __name__ == "__main__":
    asyncio.run(app.start())
