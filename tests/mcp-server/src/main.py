"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio

from microsoft.teams.ai import Function
from microsoft.teams.apps import App, AppOptions
from microsoft.teams.mcp import McpServerPlugin
from pydantic import BaseModel

mcp_server_plugin = McpServerPlugin()


class GetWeatherParams(BaseModel):
    location: str


async def get_weather_handler(params: GetWeatherParams):
    return f"The weather in {params.location} is sunny"


mcp_server_plugin.add_function(
    Function(
        name="get_weather",
        description="Get a location's weather",
        parameter_schema=GetWeatherParams,
        handler=get_weather_handler,
    )
)

app = App(AppOptions(plugins=[mcp_server_plugin]))


if __name__ == "__main__":
    asyncio.run(app.start())
