"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import importlib.metadata
import logging
from inspect import isawaitable
from typing import Annotated, Any, Awaitable, Callable, Optional, TypeVar, Union, cast

from fastmcp import FastMCP
from fastmcp.tools import FunctionTool
from microsoft_teams.ai import Function, FunctionHandler
from microsoft_teams.apps import (
    DependencyMetadata,
    FastAPIAdapter,
    HttpServer,
    Plugin,
    PluginBase,
    PluginStartEvent,
)
from pydantic import BaseModel
from starlette.requests import Request

try:
    version = importlib.metadata.version("microsoft-teams-mcpplugin")
except importlib.metadata.PackageNotFoundError:
    version = "0.0.1-alpha.1"

logger = logging.getLogger(__name__)

P = TypeVar("P", bound=BaseModel)

RequireAuthCallable = Callable[[Request], Union[bool, Awaitable[bool]]]


class _AuthMiddleware:
    """ASGI middleware that gates inbound MCP requests behind ``require_auth``."""

    def __init__(self, app: Any, require_auth: RequireAuthCallable) -> None:
        self.app = app
        self.require_auth = require_auth

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        ok = False
        try:
            result = self.require_auth(request)
            if isawaitable(result):
                result = await result
            ok = bool(result)
        except Exception:  # noqa: BLE001
            logger.debug("require_auth raised", exc_info=True)

        if not ok:
            await send(
                {
                    "type": "http.response.start",
                    "status": 401,
                    "headers": [
                        (b"content-type", b"text/plain"),
                        (b"www-authenticate", b"Bearer"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": b"unauthorized"})
            return

        await self.app(scope, receive, send)


@Plugin(name="mcp-server", version=version, description="MCP server plugin that exposes AI functions as MCP tools")
class McpServerPlugin(PluginBase):
    """
    MCP Server Plugin for Teams Apps.

    This plugin wraps FastMCP and provides a bridge between AI Functions
    and MCP tools, exposing them via streamable HTTP transport. It allows
    AI functions to be discovered and called by MCP clients.
    """

    # Dependency injection
    http_server: Annotated[HttpServer, DependencyMetadata()]

    def __init__(
        self,
        name: str = "teams-mcp-server",
        path: str = "/mcp",
        require_auth: Optional[RequireAuthCallable] = None,
    ):
        """
        Initialize the MCP server plugin.

        Args:
            name: The name of the MCP server for identification
            path: The HTTP path to mount the MCP server on (default: /mcp)
            require_auth: Optional callable gating inbound MCP requests. Receives
                a Starlette Request; return True to allow, False (or raise) to
                reject with HTTP 401. When unset, all requests are accepted and
                a warning is emitted at plugin startup.
        """
        self.mcp_server = FastMCP(name)
        self.path = path
        self._mounted = False
        self._require_auth = require_auth

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
        Add a AIfunction as an MCP tool.

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
            function: The AI function to register as an MCP tool

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
                Wrapper that adapts AI function calls to MCP format.

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
                    logger.error(f"Function execution failed for '{function.name}': {e}")
                    raise

            function_tool = FunctionTool(
                name=function.name, description=function.description, parameters=parameter_schema, fn=wrapped_handler
            )
            self.mcp_server.add_tool(function_tool)

            logger.debug(f"Registered AI function '{function.name}' as MCP tool")

            return self
        except Exception as e:
            logger.error(f"Failed to register function '{function.name}' as MCP tool: {e}")
            raise

    async def on_start(self, event: PluginStartEvent) -> None:
        """
        Start the plugin - mount MCP server on HTTP server.

        Args:
            event: Plugin start event containing application context

        Raises:
            Exception: If mounting fails
        """

        if self._mounted:
            logger.warning("MCP server already mounted")
            return

        try:
            adapter = self.http_server.adapter
            if not isinstance(adapter, FastAPIAdapter):
                raise RuntimeError("McpServerPlugin requires FastAPIAdapter. Custom adapters are not supported.")

            # We mount the mcp server as a separate app at self.path
            mcp_http_app = self.mcp_server.http_app(path=self.path, transport="http")
            adapter.lifespans.append(mcp_http_app.lifespan)  # pyright: ignore[reportArgumentType]

            if self._require_auth is not None:
                adapter.app.mount("/", _AuthMiddleware(mcp_http_app, self._require_auth))
            else:
                logger.warning(
                    "McpServerPlugin started without require_auth. All MCP requests at %s "
                    "will be accepted. Pass require_auth to enforce authentication.",
                    self.path,
                )
                adapter.app.mount("/", mcp_http_app)

            self._mounted = True

            logger.info(f"MCP server mounted at {self.path}")
        except Exception as e:
            logger.error(f"Failed to mount MCP server: {e}")
            raise

    async def on_stop(self) -> None:
        """
        Stop the plugin - clean shutdown of MCP server.

        Performs graceful shutdown of the MCP server and cleans up resources.
        """
        if self._mounted:
            logger.info("MCP server shutting down")
            self._mounted = False
