"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
from inspect import isawaitable
from logging import Logger
from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from microsoft.teams.ai import Function
from microsoft.teams.apps import (
    DependencyMetadata,
    HttpPlugin,
    LoggerDependencyOptions,
    Plugin,
    PluginBase,
    PluginStartEvent,
)
from pydantic import BaseModel
from starlette.routing import Mount

try:
    version = importlib.metadata.version("microsoft-teams-mcp")
except importlib.metadata.PackageNotFoundError:
    version = "0.0.1-alpha.1"


@Plugin(
    name="mcp-server", version=version, description="MCP server plugin that exposes Teams AI functions as MCP tools"
)
class McpServerPlugin(PluginBase):
    """
    MCP Server Plugin for Teams Apps.

    This plugin wraps FastMCP and provides a bridge between Teams AI Functions
    and MCP tools, exposing them via streamable HTTP transport.
    """

    # Dependency injection
    logger: Annotated[Logger, LoggerDependencyOptions()]
    http: Annotated[HttpPlugin, DependencyMetadata()]

    def __init__(
        self,
        name: str = "teams-mcp-server",
        path: str = "/mcp",
    ):
        """
        Initialize the MCP server plugin.

        Args:
            name: The name of the MCP server
            path: The path to mount the MCP server on (default: /mcp)
        """
        self.mcp_server = FastMCP(name)
        self.path = path
        self._mounted = False

    @property
    def server(self) -> FastMCP:
        """Get the underlying FastMCP server."""
        return self.mcp_server

    def add_function(self, function: Function[BaseModel]) -> "McpServerPlugin":
        """
        Add a Teams AI function as an MCP tool.

        Args:
            function: The Teams AI function to register as an MCP tool

        Returns:
            Self for method chaining
        """
        try:
            # Prepare parameter schema for FastMCP
            parameter_schema = (
                function.parameter_schema
                if isinstance(function.parameter_schema, dict)
                else function.parameter_schema.model_json_schema()
            )

            # Create wrapper handler that converts kwargs to the expected format
            async def wrapped_handler(**kwargs: Any) -> Any:
                try:
                    if isinstance(function.parameter_schema, type):
                        # parameter_schema is a Pydantic model class - instantiate it
                        params = function.parameter_schema(**kwargs)
                        result = function.handler(params)
                    else:
                        # parameter_schema is a dict - pass kwargs directly
                        result = function.handler(**kwargs)

                    # Handle both sync and async handlers
                    if isawaitable(result):
                        return await result
                    return result
                except Exception as e:
                    self.logger.error(f"Function execution failed for '{function.name}': {e}")
                    raise

            function_tool = FunctionTool(
                name=function.name, description=function.description, parameters=parameter_schema, fn=wrapped_handler
            )
            self.mcp_server.add_tool(function_tool)

            self.logger.info(f"Registered Teams AI function '{function.name}' as MCP tool")

            return self
        except Exception as e:
            self.logger.error(f"Failed to register function '{function.name}' as MCP tool: {e}")
            raise

    async def on_init(self) -> None:
        """Initialize the plugin."""
        self.logger.info("Initializing MCP server plugin")

    async def on_start(self, event: PluginStartEvent) -> None:
        """Start the plugin - mount MCP server on HTTP plugin."""
        if self._mounted:
            self.logger.warning("MCP server already mounted")
            return

        try:
            # Mount the MCP streamable HTTP app on the existing FastAPI server
            mount_route = Mount(self.path, app=self.mcp_server.streamable_http_app())
            self.http.app.router.routes.append(mount_route)

            self._mounted = True

            self.logger.info(f"MCP server mounted at http://localhost:{event.port}{self.path}")
        except Exception as e:
            self.logger.error(f"Failed to mount MCP server: {e}")
            raise

    async def on_stop(self) -> None:
        """Stop the plugin - clean shutdown of MCP server."""
        if self._mounted:
            self.logger.info("MCP server shutting down")
            self._mounted = False
