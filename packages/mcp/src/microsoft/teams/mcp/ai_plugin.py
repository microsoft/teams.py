"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from microsoft.teams.ai.function import Function
from microsoft.teams.ai.plugin import BaseAIPlugin
from microsoft.teams.common.logging import ConsoleLogger
from pydantic import BaseModel

from mcp import ClientSession
from mcp.types import TextContent

from .models import McpCachedValue, McpClientPluginParams, McpToolDetails
from .transport import create_transport

REFETCH_TIMEOUT_MS = 24 * 60 * 60 * 1000  # 1 day


class McpClientPlugin(BaseAIPlugin):
    """MCP Client Plugin for Teams AI integration."""

    def __init__(
        self,
        name: str = "mcp_client",
        version: str = "0.0.0",
        cache: Optional[Dict[str, McpCachedValue]] = None,
        logger: Optional[logging.Logger] = None,
        refetch_timeout_ms: int = REFETCH_TIMEOUT_MS,  # 1 day
    ):
        super().__init__(name)

        self._version = version
        self._cache: Dict[str, McpCachedValue] = cache or {}
        self._logger = logger.getChild(self.name) if logger else ConsoleLogger().create_logger(self.name)
        self._refetch_timeout_ms = refetch_timeout_ms

        # If cache is provided, update last_fetched for entries with tools
        if cache:
            current_time = time.time() * 1000
            for cached_value in cache.values():
                if cached_value.available_tools and not cached_value.last_fetched:
                    cached_value.last_fetched = current_time

        # Track MCP server URLs and their parameters
        self._mcp_server_params: Dict[str, McpClientPluginParams] = {}

    @property
    def version(self) -> str:
        """Get the plugin version."""
        return self._version

    @property
    def cache(self) -> Dict[str, McpCachedValue]:
        """Get the plugin cache."""
        return self._cache

    @property
    def refetch_timeout_ms(self) -> int:
        """Get the refetch timeout in milliseconds."""
        return self._refetch_timeout_ms

    def use_mcp_server(self, url: str, params: Optional[McpClientPluginParams] = None) -> None:
        """Add or updates an MCP server to be used by this plugin."""
        self._mcp_server_params[url] = params or McpClientPluginParams()

        # Update cache if tools are provided
        if params and params.available_tools:
            self._cache[url] = McpCachedValue(
                transport=params.transport,
                available_tools=params.available_tools,
                last_fetched=time.time() * 1000,  # Set to current time in milliseconds
            )

    async def on_build_functions(self, functions: List[Function[BaseModel]]) -> List[Function[BaseModel]]:
        """Build functions from MCP tools."""
        await self._fetch_tools_if_needed()

        # Create functions from cached tools
        all_functions = list(functions)

        for url, params in self._mcp_server_params.items():
            cached_data = self._cache.get(url)
            available_tools = cached_data.available_tools if cached_data else []

            for tool in available_tools:
                # Create a function for each tool
                function = self._create_function_from_tool(url, tool, params)
                all_functions.append(function)

        return all_functions

    async def _fetch_tools_if_needed(self) -> None:
        """
        Fetch tools from MCP servers if needed.

        We check if there the cached value has met its expiration
        for being refetched. Or if the tools have never been fetched at all
        """
        fetch_needed: List[Tuple[str, McpClientPluginParams]] = []
        current_time = time.time() * 1000  # Convert to milliseconds

        for url, params in self._mcp_server_params.items():
            # Skip if tools are explicitly provided
            if params.available_tools:
                continue

            cached_data = self._cache.get(url)
            should_fetch = (
                not cached_data
                or not cached_data.available_tools
                or not cached_data.last_fetched
                or (current_time - cached_data.last_fetched) > (params.refetch_timeout_ms or self._refetch_timeout_ms)
            )

            if should_fetch:
                fetch_needed.append((url, params))

        # Fetch tools in parallel
        if fetch_needed:
            tasks = [self._fetch_tools_from_server(url, params) for url, params in fetch_needed]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, (url, params) in enumerate(fetch_needed):
                result = results[i]
                if isinstance(result, Exception):
                    self._logger.error(f"Failed to fetch tools from {url}: {result}")
                    if not params.skip_if_unavailable:
                        raise result
                elif isinstance(result, list):
                    # Update cache with fetched tools
                    if url not in self._cache:
                        self._cache[url] = McpCachedValue()
                    self._cache[url].available_tools = result
                    self._cache[url].last_fetched = current_time
                    self._cache[url].transport = params.transport

                    self._logger.debug(f"Cached {len(result)} tools for {url}")

    def _create_function_from_tool(
        self, url: str, tool: McpToolDetails, plugin_params: McpClientPluginParams
    ) -> Function[BaseModel]:
        """Create a Teams AI function from an MCP tool."""
        tool_name = tool.name
        tool_description = tool.description

        async def handler(params: BaseModel) -> str:
            """Handle MCP tool call."""
            try:
                self._logger.debug(f"Making call to {url} tool-name={tool_name}")
                result = await self._call_mcp_tool(url, tool_name, params.model_dump(), plugin_params)
                self._logger.debug(f"Successfully received result for mcp call {result}")
                return str(result)
            except Exception as e:
                self._logger.error(f"Error calling tool {tool_name} on {url}: {e}")
                raise

        return Function(
            name=tool_name, description=tool_description, parameter_schema=tool.input_schema, handler=handler
        )

    async def _fetch_tools_from_server(self, url: str, params: McpClientPluginParams) -> List[McpToolDetails]:
        """Fetch tools from a specific MCP server."""
        transport_context = create_transport(url, params.transport or "streamable_http", params.headers)

        async with transport_context as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                # List available tools
                tools_response = await session.list_tools()

                # Convert MCP tools to our format
                tools: list[McpToolDetails] = []
                for tool in tools_response.tools:
                    tools.append(
                        McpToolDetails(
                            name=tool.name, description=tool.description or "", input_schema=tool.inputSchema or {}
                        )
                    )

                self._logger.debug(f"Got {len(tools)} tools for {url}")
                return tools

    async def _call_mcp_tool(
        self, url: str, tool_name: str, arguments: Dict[str, Any], params: McpClientPluginParams
    ) -> Optional[Union[str, List[str]]]:
        """Call a specific tool on an MCP server."""
        transport_context = create_transport(url, params.transport or "streamable_http", params.headers)

        async with transport_context as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                # Initialize the connection
                await session.initialize()

                # Call the tool
                result = await session.call_tool(tool_name, arguments)

                # Return the content from the result
                if result.content:
                    if len(result.content) == 1:
                        content_item = result.content[0]
                        if isinstance(content_item, TextContent):
                            return content_item.text
                        else:
                            return str(content_item)
                    else:
                        contents: list[str] = []
                        for item in result.content:
                            if isinstance(item, TextContent):
                                contents.append(item.text)
                            else:
                                try:
                                    contents.append(json.dumps(item, default=str, ensure_ascii=False))
                                except (TypeError, ValueError) as e:
                                    self._logger.warning(f"Failed to serialize content item: {e}")
                                    contents.append(str(item))
                        return contents

                return None
