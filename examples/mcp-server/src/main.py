"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from typing import Dict

from microsoft_teams.ai import Function
from microsoft_teams.api.activities.message.message import MessageActivity
from microsoft_teams.apps import App
from microsoft_teams.apps.routing.activity_context import ActivityContext
from microsoft_teams.devtools import DevToolsPlugin
from microsoft_teams.mcpplugin import McpServerPlugin
from pydantic import BaseModel

# Configure MCP server with custom name (as shown in docs)
mcp_server_plugin = McpServerPlugin(
    name="test-mcp",
)

# Storage for conversation IDs (for proactive messaging)
conversation_storage: Dict[str, str] = {}


# Echo tool from documentation example
class EchoParams(BaseModel):
    input: str


async def echo_handler(params: EchoParams) -> str:
    return f"You said {params.input}"


# Weather tool (existing)
class GetWeatherParams(BaseModel):
    location: str


async def get_weather_handler(params: GetWeatherParams):
    return f"The weather in {params.location} is sunny"


class CalculateParams(BaseModel):
    operation: str
    a: float
    b: float


async def calculate_handler(params: CalculateParams) -> str:
    match params.operation:
        case "add":
            return str(params.a + params.b)
        case "subtract":
            return str(params.a - params.b)
        case "multiply":
            return str(params.a * params.b)
        case "divide":
            return str(params.a / params.b) if params.b != 0 else "Cannot divide by zero"
        case _:
            return "Unknown operation"


# Alert tool for proactive messaging (as mentioned in docs)
class AlertParams(BaseModel):
    user_id: str
    message: str


async def alert_handler(params: AlertParams) -> str:
    """
    Send proactive message to user via Teams.
    This demonstrates the "piping messages to user" feature from docs.
    """
    # 1. Validate if the incoming request is allowed to send messages
    if not params.user_id or not params.message:
        return "Invalid parameters: user_id and message are required"

    # 2. Fetch the correct conversation ID for the given user
    conversation_id = conversation_storage.get(params.user_id)
    if not conversation_id:
        return f"No conversation found for user {params.user_id}. User needs to message the bot first."

    # 3. Send proactive message (simplified - in real implementation would use proper proactive messaging)
    await app.send(conversation_id=conversation_id, activity=params.message)
    return f"Alert sent to user {params.user_id}: {params.message} (conversation: {conversation_id})"


# Register echo tool (from documentation)
mcp_server_plugin.use_tool(
    Function(
        name="echo",
        description="echo back whatever you said",
        parameter_schema=EchoParams,
        handler=echo_handler,
    )
)

# Register weather tool
mcp_server_plugin.use_tool(
    Function(
        name="get_weather",
        description="Get a location's weather",
        parameter_schema=GetWeatherParams,
        handler=get_weather_handler,
    )
)

# Register calculator tool
mcp_server_plugin.use_tool(
    Function(
        name="calculate",
        description="Perform basic arithmetic operations",
        parameter_schema=CalculateParams,
        handler=calculate_handler,
    )
)

# Register alert tool for proactive messaging
mcp_server_plugin.use_tool(
    Function(
        name="alert",
        description="Send proactive message to a Teams user",
        parameter_schema=AlertParams,
        handler=alert_handler,
    )
)

app = App(plugins=[mcp_server_plugin, DevToolsPlugin()])


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    """
    Handle incoming messages and store conversation IDs for proactive messaging.
    This demonstrates the conversation ID storage mentioned in the docs.
    """
    # Store conversation ID for this user (for proactive messaging)
    user_id = ctx.activity.from_.id
    conversation_id = ctx.activity.conversation.id
    conversation_storage[user_id] = conversation_id

    print(f"User {ctx.activity.from_} just sent a message!")

    # Echo back the message with info about stored conversation
    await ctx.reply(
        f"You said: {ctx.activity.text}\n\n"
        f"📝 Stored conversation ID `{conversation_id}` for user `{user_id}` "
        f"(for proactive messaging via MCP alert tool)"
    )


if __name__ == "__main__":
    asyncio.run(app.start())
