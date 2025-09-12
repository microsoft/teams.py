"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

import pytest
from mcp.types import CallToolResult, ContentBlock, ListToolsResult, TextContent, Tool
from microsoft.teams.mcpplugin.models import McpToolDetails

# pyright: basic


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
        self.called_tools = []

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
            content: list[ContentBlock] = [TextContent(type="text", text=item) for item in response]
        else:
            content = [TextContent(type="text", text=str(response))]

        return CallToolResult(content=content)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockTransport:
    """Mock transport for MCP connections."""

    def __init__(self, session: MockClientSession):
        self.session = session
        self.headers_received = {}

    @asynccontextmanager
    async def create_transport(self, url: str, transport_type: str, headers: Optional[Dict] = None):
        if headers:
            # Resolve any callable headers
            resolved_headers = {}
            for key, value in headers.items():
                if callable(value):
                    if asyncio.iscoroutinefunction(value):
                        resolved_headers[key] = await value()
                    else:
                        resolved_headers[key] = value()
                else:
                    resolved_headers[key] = value
            self.headers_received = resolved_headers

        # Simulate read/write streams
        read_stream = MagicMock()
        write_stream = MagicMock()
        yield (read_stream, write_stream)


@pytest.fixture
def mock_client_session():
    """Fixture providing a mock MCP client session."""

    def _create_session(tools: Optional[List[MockMCPTool]] = None, call_responses: Optional[Dict[str, Any]] = None):
        return MockClientSession(tools=tools, call_responses=call_responses)

    return _create_session


@pytest.fixture
def mock_transport():
    """Fixture providing a mock transport."""

    def _create_transport(session: MockClientSession):
        return MockTransport(session)

    return _create_transport


@pytest.fixture
def sample_tools():
    """Fixture providing sample MCP tools for testing."""
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


@pytest.fixture
def sample_tool_details(sample_tools):
    """Fixture providing sample McpToolDetails for testing."""
    return [
        McpToolDetails(name=tool.name, description=tool.description, input_schema=tool.inputSchema)
        for tool in sample_tools
    ]
