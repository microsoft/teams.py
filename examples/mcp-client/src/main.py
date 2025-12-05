"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import re
from os import getenv

from dotenv import find_dotenv, load_dotenv
from microsoft_teams.ai import ChatPrompt, ListMemory
from microsoft_teams.api import MessageActivity, MessageActivityInput, TypingActivityInput
from microsoft_teams.apps import ActivityContext, App
from microsoft_teams.devtools import DevToolsPlugin
from microsoft_teams.mcpplugin import McpClientPlugin, McpClientPluginParams
from microsoft_teams.openai import OpenAICompletionsAIModel, OpenAIResponsesAIModel

load_dotenv(find_dotenv(usecwd=True))

app = App(plugins=[DevToolsPlugin()])


def get_required_env(key: str) -> str:
    value = getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


AZURE_OPENAI_MODEL = get_required_env("AZURE_OPENAI_MODEL")


# GitHub PAT for MCP server (optional)
def get_optional_env(key: str) -> str | None:
    return getenv(key)


# This example uses a PersonalAccessToken, but you may get
# the user's oauth token as well by getting them to sign in
# and then using app.sign_in to get their token.
GITHUB_PAT = get_optional_env("GITHUB_PAT")

# Set up AI models
completions_model = OpenAICompletionsAIModel(model=AZURE_OPENAI_MODEL)
responses_model = OpenAIResponsesAIModel(model=AZURE_OPENAI_MODEL, stateful=True)

# Configure MCP Client Plugin with multiple remote servers (as shown in docs)
mcp_plugin = McpClientPlugin()

# Add multiple MCP servers to demonstrate the concept from documentation
mcp_plugin.use_mcp_server("https://learn.microsoft.com/api/mcp")

# Add GitHub MCP server with authentication headers (demonstrates header functionality)
if GITHUB_PAT:
    mcp_plugin.use_mcp_server(
        "https://api.githubcopilot.com/mcp/", McpClientPluginParams(headers={"Authorization": f"Bearer {GITHUB_PAT}"})
    )
    print("✅ GitHub MCP server configured with authentication")
else:
    print("⚠️  GITHUB_PAT not found - GitHub MCP server not configured")
    print("   Set GITHUB_PAT environment variable to enable GitHub MCP integration")
# Example of additional servers (commented out - would need actual working endpoints):
# mcp_plugin.use_mcp_server("https://example.com/mcp/weather")
# mcp_plugin.use_mcp_server("https://example.com/mcp/pokemon")

# Memory for stateful conversations
chat_memory = ListMemory()

# ChatPrompt using Responses API with MCP tools (stateful)
responses_prompt = ChatPrompt(responses_model, memory=chat_memory, plugins=[mcp_plugin])

# ChatPrompt with MCP tools (demonstrating docs example)
chat_prompt = ChatPrompt(completions_model, plugins=[mcp_plugin])


# Pattern-based handlers to demonstrate different MCP usage patterns


@app.on_message_pattern(re.compile(r"^agent\s+(.+)", re.IGNORECASE))
async def handle_agent_chat(ctx: ActivityContext[MessageActivity]):
    """Handle 'agent <query>' command using ChatPrompt with MCP tools (stateful)"""
    match = re.match(r"^agent\s+(.+)", ctx.activity.text, re.IGNORECASE)
    if match:
        query = match.group(1).strip()

        print(f"[AGENT] Processing: {query}")
        await ctx.send(TypingActivityInput())

        # Use ChatPrompt with MCP tools (stateful conversation)
        result = await responses_prompt.send(query)
        if result.response.content:
            message = MessageActivityInput(text=result.response.content).add_ai_generated()
            await ctx.send(message)


@app.on_message_pattern(re.compile(r"^prompt\s+(.+)", re.IGNORECASE))
async def handle_prompt_chat(ctx: ActivityContext[MessageActivity]):
    """Handle 'prompt <query>' command using ChatPrompt with MCP tools (stateless)"""
    match = re.match(r"^prompt\s+(.+)", ctx.activity.text, re.IGNORECASE)
    if match:
        query = match.group(1).strip()

        print(f"[PROMPT] Processing: {query}")
        await ctx.send(TypingActivityInput())

        # Use ChatPrompt with MCP tools (demonstrates docs pattern)
        result = await chat_prompt.send(
            input=query,
            instructions=(
                "You are a helpful assistant with access to remote MCP tools.Use them to help answer questions."
            ),
        )

        if result.response.content:
            message = MessageActivityInput(text=result.response.content).add_ai_generated()
            await ctx.send(message)


@app.on_message_pattern(re.compile(r"^mcp\s+info", re.IGNORECASE))
async def handle_mcp_info(ctx: ActivityContext[MessageActivity]):
    """Handle 'mcp info' command to show available MCP servers and tools"""
    # Build server list dynamically based on what's configured
    servers_info = "**Connected MCP Servers:**\n"
    servers_info += "• `https://learn.microsoft.com/api/mcp` - Microsoft Learn API\n"

    if GITHUB_PAT:
        servers_info += "• `https://api.githubcopilot.com/mcp/` - GitHub Copilot API (authenticated)\n"
    else:
        servers_info += "• GitHub MCP server (not configured - set GITHUB_PAT env var)\n"

    info_text = (
        "🔗 **MCP Client Information**\n\n"
        f"{servers_info}\n"
        "**Authentication Demo:**\n"
        "• GitHub server uses Bearer token authentication via headers\n"
        "• Example: `headers={'Authorization': f'Bearer {GITHUB_PAT}'}`\n\n"
        "**Usage Patterns:**\n"
        "• `agent <query>` - Use stateful Agent with MCP tools\n"
        "• `prompt <query>` - Use stateless ChatPrompt with MCP tools\n"
        "• `mcp info` - Show this information\n\n"
        "**How it works:**\n"
        "1. MCP Client connects to remote servers via SSE protocol\n"
        "2. Headers (like Authorization) are passed with each request\n"
        "3. Remote tools are loaded and integrated with ChatPrompt/Agent\n"
        "4. LLM can call remote tools as needed to answer your questions"
    )
    await ctx.reply(info_text)


# Fallback handler for general chat (uses ChatPrompt by default)
@app.on_message
async def handle_fallback_message(ctx: ActivityContext[MessageActivity]):
    """Fallback handler using ChatPrompt with MCP tools"""
    print(f"[FALLBACK] Message received: {ctx.activity.text}")
    print(f"[FALLBACK] From: {ctx.activity.from_}")
    await ctx.send(TypingActivityInput())

    # Use ChatPrompt with MCP tools for general conversation
    result = await responses_prompt.send(ctx.activity.text)
    if result.response.content:
        message = MessageActivityInput(text=result.response.content).add_ai_generated()
        await ctx.send(message)


if __name__ == "__main__":
    asyncio.run(app.start())
