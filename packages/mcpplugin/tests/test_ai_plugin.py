"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import inspect
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolResult, ContentBlock, ListToolsResult, TextContent, Tool
from microsoft.teams.mcpplugin.ai_plugin import McpClientPlugin
from microsoft.teams.mcpplugin.models import McpCachedValue, McpClientPluginParams, McpToolDetails
from pydantic import BaseModel

# pyright: basic


async def call_handler(handler, params):
    """Utility to handle both sync and async function handlers."""
    result = handler(params)
    if inspect.iscoroutine(result):
        return await result
    return result


class MockMCPTool:
    """Mock MCP tool for testing."""

    def __init__(self, name: str, description: str = "", input_schema: Optional[Dict[str, Any]] = None):
        self.name = name
        self.description = description
        self.inputSchema = input_schema or {}


class MockClientSession:
    """Mock MCP client session."""

    def __init__(self, tools: Optional[List[MockMCPTool]] = None, call_responses: Optional[Dict[str, Any]] = None):
        self.tools = tools or []
        self.call_responses = call_responses or {}
        self.initialize_called = False
        self.list_tools_called = False
        self.called_tools: List[Tuple[str, Dict[str, Any]]] = []

    async def initialize(self):
        self.initialize_called = True

    async def list_tools(self) -> ListToolsResult:
        self.list_tools_called = True
        mcp_tools = [
            Tool(name=tool.name, description=tool.description, inputSchema=tool.inputSchema) for tool in self.tools
        ]
        return ListToolsResult(tools=mcp_tools)

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        self.called_tools.append((tool_name, arguments))
        response = self.call_responses.get(tool_name, "Mock response")

        if isinstance(response, Exception):
            raise response

        if isinstance(response, list):
            content: List[ContentBlock] = [TextContent(type="text", text=str(item)) for item in response]
        else:
            content = [TextContent(type="text", text=str(response))]

        return CallToolResult(content=content)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any):
        pass


class MockTransport:
    """Mock transport for MCP connections."""

    def __init__(self, session: MockClientSession):
        self.session = session
        self.headers_received: Dict[str, str] = {}

    @asynccontextmanager
    async def create_transport(self, url: str, transport_type: str, headers: Optional[Dict[str, Any]] = None):
        if headers:
            # Resolve any callable headers
            resolved_headers: Dict[str, str] = {}
            for key, value in headers.items():
                if callable(value):
                    if asyncio.iscoroutinefunction(value):
                        resolved_headers[key] = str(await value())
                    else:
                        resolved_headers[key] = str(value())
                else:
                    resolved_headers[key] = str(value)
            self.headers_received = resolved_headers

        # Simulate read/write streams
        read_stream = MagicMock()
        write_stream = MagicMock()
        yield (read_stream, write_stream)


@pytest.fixture
def sample_tools() -> List[MockMCPTool]:
    """Sample MCP tools for testing."""
    return [
        MockMCPTool(
            name="calculator",
            description="Perform mathematical calculations",
            input_schema={
                "type": "object",
                "properties": {"expression": {"type": "string", "description": "Mathematical expression"}},
                "required": ["expression"],
            },
        ),
        MockMCPTool(
            name="weather",
            description="Get weather information",
            input_schema={},  # Tool without parameters
        ),
        MockMCPTool(
            name="echo",
            description="Echo back the input",
            input_schema={"type": "object", "properties": {"message": {"type": "string"}}},
        ),
    ]


class TestMcpClientPlugin:
    """Comprehensive tests for MCP Client Plugin."""

    # Tool Retrieval Tests
    @pytest.mark.asyncio
    async def test_tool_retrieval_with_parameters(self, sample_tools: List[MockMCPTool]):
        """Test that tools with input parameters are properly retrieved."""
        session = MockClientSession(tools=[sample_tools[0]])  # calculator tool

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            functions = await plugin.on_build_functions([])

            assert len(functions) == 1
            function = functions[0]
            assert function.name == "calculator"
            assert function.description == "Perform mathematical calculations"
            assert isinstance(function.parameter_schema, dict)
            assert "expression" in function.parameter_schema["properties"]
            assert session.initialize_called
            assert session.list_tools_called

    @pytest.mark.asyncio
    async def test_tool_retrieval_without_parameters(self, sample_tools: List[MockMCPTool]):
        """Test that tools without input parameters are handled correctly."""
        session = MockClientSession(tools=[sample_tools[1]])  # weather tool

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            functions = await plugin.on_build_functions([])

            assert len(functions) == 1
            function = functions[0]
            assert function.name == "weather"
            assert function.description == "Get weather information"
            assert function.parameter_schema == {}

    # Caching Tests
    @pytest.mark.asyncio
    async def test_tools_cached_after_first_fetch(self, sample_tools: List[MockMCPTool]):
        """Test that tools are cached after initial retrieval."""
        session = MockClientSession(tools=sample_tools[:1])

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            await plugin.on_build_functions([])

            assert "http://test-server" in plugin.cache
            cached_data = plugin.cache["http://test-server"]
            assert len(cached_data.available_tools) == 1
            assert cached_data.available_tools[0].name == "calculator"
            assert cached_data.last_fetched is not None

    @pytest.mark.asyncio
    async def test_no_refetch_within_timeout(self, sample_tools: List[MockMCPTool]):
        """Test that no refetch occurs within timeout period."""
        session = MockClientSession(tools=sample_tools[:1])

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin(refetch_timeout_ms=60000)  # 1 minute
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            await plugin.on_build_functions([])
            first_call_count = mock_create_transport.call_count

            await plugin.on_build_functions([])
            second_call_count = mock_create_transport.call_count

            assert second_call_count == first_call_count

    # Header Tests
    @pytest.mark.asyncio
    async def test_static_headers_sent_correctly(self, sample_tools: List[MockMCPTool]):
        """Test that static header values are transmitted correctly."""
        session = MockClientSession(tools=sample_tools[:1])
        transport = MockTransport(session)

        headers = {"Authorization": "Bearer test-token", "X-Client-Version": "1.0.0"}

        with (
            patch(
                "microsoft.teams.mcpplugin.ai_plugin.create_transport",
                return_value=transport.create_transport("http://test-server", "streamable_http", headers),
            ),
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            plugin = McpClientPlugin()
            params = McpClientPluginParams(headers=headers)
            plugin.use_mcp_server("http://test-server", params)

            await plugin.on_build_functions([])

            assert transport.headers_received["Authorization"] == "Bearer test-token"
            assert transport.headers_received["X-Client-Version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_dynamic_headers_called_and_sent(self, sample_tools: List[MockMCPTool]):
        """Test that dynamic header functions are called and values sent."""
        session = MockClientSession(tools=sample_tools[:1])
        transport = MockTransport(session)

        def get_auth_token():
            return "Bearer dynamic-token"

        async def get_async_session_id():
            return "session-abc123"

        headers = {
            "Authorization": get_auth_token,
            "X-Session-ID": get_async_session_id,
            "Content-Type": "application/json",
        }

        with (
            patch(
                "microsoft.teams.mcpplugin.ai_plugin.create_transport",
                return_value=transport.create_transport("http://test-server", "streamable_http", headers),
            ),
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            plugin = McpClientPlugin()
            params = McpClientPluginParams(headers=headers)
            plugin.use_mcp_server("http://test-server", params)

            await plugin.on_build_functions([])

            assert transport.headers_received["Authorization"] == "Bearer dynamic-token"
            assert transport.headers_received["X-Session-ID"] == "session-abc123"
            assert transport.headers_received["Content-Type"] == "application/json"

    # Function Creation Tests
    @pytest.mark.asyncio
    async def test_function_handler_calls_mcp_tool(self, sample_tools: List[MockMCPTool]):
        """Test that function handlers properly call MCP tools."""
        session = MockClientSession(tools=[sample_tools[0]], call_responses={"calculator": "Result: 42"})

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            functions = await plugin.on_build_functions([])
            calculator_function = functions[0]

            class CalculatorParams(BaseModel):
                expression: str = "2+2"

            params = CalculatorParams()
            result = await call_handler(calculator_function.handler, params)

            assert len(session.called_tools) == 1
            tool_call = session.called_tools[0]
            assert tool_call[0] == "calculator"
            assert tool_call[1] == {"expression": "2+2"}
            assert result == "Result: 42"

    @pytest.mark.asyncio
    async def test_multiple_content_items_handling(self, sample_tools: List[MockMCPTool]):
        """Test that functions handle multiple content items in responses."""
        session = MockClientSession(
            tools=[sample_tools[0]], call_responses={"calculator": ["First result", "Second result"]}
        )

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            functions = await plugin.on_build_functions([])
            calculator_function = functions[0]

            class CalculatorParams(BaseModel):
                expression: str = "complex_calc"

            result = await call_handler(calculator_function.handler, CalculatorParams())
            expected = ["First result", "Second result"]
            assert result == str(expected)

    # Error Handling Tests
    @pytest.mark.asyncio
    async def test_server_unavailable_with_skip_flag(self):
        """Test graceful handling when server unavailable and skip_if_unavailable=True."""
        connection_error = ConnectionError("Server unavailable")

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", side_effect=connection_error),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(side_effect=connection_error)
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            params = McpClientPluginParams(skip_if_unavailable=True)
            plugin.use_mcp_server("http://unavailable-server", params)

            functions = await plugin.on_build_functions([])
            assert len(functions) == 0

    @pytest.mark.asyncio
    async def test_server_unavailable_without_skip_flag(self):
        """Test exception raised when server unavailable and skip_if_unavailable=False."""
        connection_error = ConnectionError("Server unavailable")

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", side_effect=connection_error),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(side_effect=connection_error)
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            params = McpClientPluginParams(skip_if_unavailable=False)
            plugin.use_mcp_server("http://unavailable-server", params)

            with pytest.raises(ConnectionError, match="Server unavailable"):
                await plugin.on_build_functions([])

    @pytest.mark.asyncio
    async def test_tool_call_error_handling(self, sample_tools: List[MockMCPTool]):
        """Test proper error handling during tool execution."""
        tool_error = RuntimeError("Tool execution failed")
        session = MockClientSession(tools=[sample_tools[0]], call_responses={"calculator": tool_error})

        with (
            patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport,
            patch("microsoft.teams.mcpplugin.ai_plugin.ClientSession", return_value=session),
        ):
            mock_create_transport.return_value.__aenter__ = AsyncMock(return_value=(None, None))
            mock_create_transport.return_value.__aexit__ = AsyncMock(return_value=None)

            plugin = McpClientPlugin()
            plugin.use_mcp_server("http://test-server", McpClientPluginParams())

            functions = await plugin.on_build_functions([])
            calculator_function = functions[0]

            class CalculatorParams(BaseModel):
                expression: str = "invalid"

            with pytest.raises(RuntimeError, match="Tool execution failed"):
                await call_handler(calculator_function.handler, CalculatorParams())

    # Integration Tests
    @pytest.mark.asyncio
    async def test_cache_initialization_with_provided_cache(self, sample_tools: List[MockMCPTool]):
        """Test that cache is properly initialized with pre-existing data."""
        tool_details = [
            McpToolDetails(name=tool.name, description=tool.description, input_schema=tool.inputSchema)
            for tool in sample_tools[:2]
        ]

        cached_value = McpCachedValue(
            transport="streamable_http", available_tools=tool_details, last_fetched=time.time() * 1000
        )
        initial_cache = {"http://test-server": cached_value}

        plugin = McpClientPlugin(cache=initial_cache)
        plugin.use_mcp_server("http://test-server", McpClientPluginParams())

        with patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport:
            functions = await plugin.on_build_functions([])

            assert len(functions) == 2
            assert not mock_create_transport.called
            function_names = [f.name for f in functions]
            assert "calculator" in function_names
            assert "weather" in function_names

    @pytest.mark.asyncio
    async def test_predefined_tools_not_fetched(self, sample_tools: List[MockMCPTool]):
        """Test that predefined tools are not fetched from server."""
        tool_details = [
            McpToolDetails(name=tool.name, description=tool.description, input_schema=tool.inputSchema)
            for tool in sample_tools[:2]
        ]

        plugin = McpClientPlugin()
        params = McpClientPluginParams(available_tools=tool_details)
        plugin.use_mcp_server("http://test-server", params)

        with patch("microsoft.teams.mcpplugin.ai_plugin.create_transport") as mock_create_transport:
            functions = await plugin.on_build_functions([])

            assert len(functions) == 2
            assert not mock_create_transport.called
            function_names = [f.name for f in functions]
            assert "calculator" in function_names
            assert "weather" in function_names
