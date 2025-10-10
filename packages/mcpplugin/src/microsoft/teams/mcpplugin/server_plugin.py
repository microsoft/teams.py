"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
import logging
from inspect import isawaitable
from typing import Annotated, Any, TypeVar, cast

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from microsoft.teams.ai import Function, FunctionHandler
from microsoft.teams.apps import (
    DependencyMetadata,
    HttpPlugin,
    Plugin,
    PluginBase,
    PluginStartEvent,
)
from microsoft.teams.common.logging import ConsoleLogger
from pydantic import BaseModel

try:
    version = importlib.metadata.version("microsoft-teams-mcpplugin")
except importlib.metadata.PackageNotFoundError:
    version = "0.0.1-alpha.1"

P = TypeVar("P", bound=BaseModel)


@Plugin(
    name="mcp-server", version=version, description="MCP server plugin that exposes Teams AI functions as MCP tools"
)
class McpServerPlugin(PluginBase):
    """
    MCP Server Plugin for Teams Apps.

    This plugin wraps FastMCP and provides a bridge between Teams AI Functions
    and MCP tools, exposing them via streamable HTTP transport. It allows
    Teams AI functions to be discovered and called by MCP clients.
    """

    # Dependency injection
    http: Annotated[HttpPlugin, DependencyMetadata()]

    def __init__(self, name: str = "teams-mcp-server", path: str = "/mcp", logger: logging.Logger | None = None):
        """
        Initialize the MCP server plugin.

        Args:
            name: The name of the MCP server for identification
            path: The HTTP path to mount the MCP server on (default: /mcp)
            logger: Optional logger instance for debugging
        """
        self.mcp_server = FastMCP(name)
        self.path = path
        self._mounted = False
        self.logger = logger or ConsoleLogger().create_logger("mcp-server")

    @property
    def server(self) -> FastMCP:
        """
        Get the underlying FastMCP server.

        Returns:
            FastMCP server instance for direct access to MCP functionality
        """
        return self.mcp_server

    def use_tool(self, function: Function[P]) -> "McpServerPlugin":
        """
        Add a Teams AI function as an MCP tool.

        This a convenience wrapper on top of the underlying FastMCP's add_tool.
        Use it like:
        ```py
        mcp_server_plugin.use_tool(my_fn_definition)
        ```

        If you'd like to use that directly, you can call
        ```py
        @mcp_server_plugin.server.tool
        def my_fn_definition(arg1: int, arg2: str): bool
            ...
        ```

        Args:
            function: The Teams AI function to register as an MCP tool

        Returns:
            Self for method chaining
        """
        try:
            # Prepare parameter schema for FastMCP
            parameter_schema = {}

            if isinstance(function.parameter_schema, dict):
                parameter_schema = function.parameter_schema
            elif function.parameter_schema:
                parameter_schema = function.parameter_schema.model_json_schema()

            # Create wrapper handler that converts kwargs to the expected format
            async def wrapped_handler(**kwargs: Any) -> Any:
                """
                Wrapper that adapts Teams AI function calls to MCP format.

                Args:
                    **kwargs: Function arguments from MCP client

                Returns:
                    Function execution result

                Raises:
                    Exception: If function execution fails
                """
                try:
                    if isinstance(function.parameter_schema, type):
                        # parameter_schema is a Pydantic model class - instantiate it
                        params = function.parameter_schema(**kwargs)
                        handler = cast(FunctionHandler[BaseModel], function.handler)
                        result = handler(params)
                    else:
                        # parameter_schema is a dict or None - pass kwargs directly
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

            self.logger.debug(f"Registered Teams AI function '{function.name}' as MCP tool")

            return self
        except Exception as e:
            self.logger.error(f"Failed to register function '{function.name}' as MCP tool: {e}")
            raise

    async def on_start(self, event: PluginStartEvent) -> None:
        """
        Start the plugin - mount MCP server on HTTP plugin.

        Args:
            event: Plugin start event containing application context

        Raises:
            Exception: If mounting fails
        """

        if self._mounted:
            self.logger.warning("MCP server already mounted")
            return

        try:
            # We mount the mcp server as a separate app at self.path
            mcp_http_app = self.mcp_server.http_app(path=self.path, transport="http")
            self.http.lifespans.append(mcp_http_app.lifespan)
            self.http.app.mount("/", mcp_http_app)

            self._mounted = True

            self.logger.info(f"MCP server mounted at {self.path}")
        except Exception as e:
            self.logger.error(f"Failed to mount MCP server: {e}")
            raise

    async def on_stop(self) -> None:
        """
        Stop the plugin - clean shutdown of MCP server.

        Performs graceful shutdown of the MCP server and cleans up resources.
        """
        if self._mounted:
            self.logger.info("MCP server shutting down")
            self._mounted = False
