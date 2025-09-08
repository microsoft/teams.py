"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft.teams.ai import Function
from microsoft.teams.api.activities.message.message import MessageActivity
from microsoft.teams.apps import App
from microsoft.teams.apps.routing.activity_context import ActivityContext
from microsoft.teams.devtools import DevToolsPlugin
from microsoft.teams.mcp import McpServerPlugin
from pydantic import BaseModel

mcp_server_plugin = McpServerPlugin()


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


# Direct function call usage
mcp_server_plugin.use_tool(
    Function(
        name="get_weather",
        description="Get a location's weather",
        parameter_schema=GetWeatherParams,
        handler=get_weather_handler,
    )
)

# Second tool registration
mcp_server_plugin.use_tool(
    Function(
        name="calculate",
        description="Perform basic arithmetic operations",
        parameter_schema=CalculateParams,
        handler=calculate_handler,
    )
)

app = App(plugins=[mcp_server_plugin, DevToolsPlugin()])


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]):
    await ctx.reply(f"You said {ctx.activity.text}")


if __name__ == "__main__":
    asyncio.run(app.start())
