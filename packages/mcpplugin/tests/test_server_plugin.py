"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import MagicMock, patch

import pytest
from microsoft_teams.ai import Function
from microsoft_teams.apps import FastAPIAdapter, HttpServer, PluginStartEvent
from microsoft_teams.mcpplugin.server_plugin import McpServerPlugin
from pydantic import BaseModel, ValidationError

# pyright: basic


class TestMcpServerPluginInit:
    """Tests for McpServerPlugin.__init__"""

    def test_init_default_args(self):
        """Test __init__ with default arguments creates correct state."""
        with patch("microsoft_teams.mcpplugin.server_plugin.FastMCP") as mock_fastmcp_class:
            mock_fastmcp_instance = MagicMock()
            mock_fastmcp_class.return_value = mock_fastmcp_instance

            plugin = McpServerPlugin()

            mock_fastmcp_class.assert_called_once_with("teams-mcp-server")
            assert plugin.mcp_server is mock_fastmcp_instance
            assert plugin.path == "/mcp"
            assert plugin._mounted is False

    def test_init_custom_args(self):
        """Test __init__ with custom name and path."""
        with patch("microsoft_teams.mcpplugin.server_plugin.FastMCP") as mock_fastmcp_class:
            mock_fastmcp_instance = MagicMock()
            mock_fastmcp_class.return_value = mock_fastmcp_instance

            plugin = McpServerPlugin(name="my-mcp-server", path="/custom-mcp")

            mock_fastmcp_class.assert_called_once_with("my-mcp-server")
            assert plugin.mcp_server is mock_fastmcp_instance
            assert plugin.path == "/custom-mcp"
            assert plugin._mounted is False


class TestMcpServerPluginUseTool:
    """Tests for McpServerPlugin.use_tool method."""

    @pytest.fixture
    def mock_mcp_server(self):
        return MagicMock()

    @pytest.fixture
    def plugin(self, mock_mcp_server: MagicMock):
        with patch("microsoft_teams.mcpplugin.server_plugin.FastMCP") as mock_fastmcp_class:
            mock_fastmcp_class.return_value = mock_mcp_server
            p = McpServerPlugin()
            yield p

    def test_use_tool_with_dict_schema(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """Test use_tool registers a function with dict parameter schema."""
        dict_schema = {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        }

        def sync_handler(**kwargs):
            return f"result: {kwargs.get('query')}"

        function = Function(
            name="search",
            description="Search for something",
            parameter_schema=dict_schema,
            handler=sync_handler,
        )

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_function_tool_class:
            mock_tool_instance = MagicMock()
            mock_function_tool_class.return_value = mock_tool_instance

            result = plugin.use_tool(function)

            assert result is plugin

            mock_function_tool_class.assert_called_once()
            call_kwargs = mock_function_tool_class.call_args.kwargs
            assert call_kwargs["name"] == "search"
            assert call_kwargs["description"] == "Search for something"
            assert call_kwargs["parameters"] == dict_schema

            mock_mcp_server.add_tool.assert_called_once_with(mock_tool_instance)

    def test_use_tool_with_pydantic_model_schema(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """Test use_tool with a Pydantic model as parameter schema."""

        class SearchParams(BaseModel):
            query: str
            limit: int = 10

        def handler(params: SearchParams):
            return f"searched: {params.query}"

        function = Function[SearchParams](
            name="pydantic_search",
            description="Search with pydantic params",
            parameter_schema=SearchParams,
            handler=handler,
        )

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_function_tool_class:
            mock_tool_instance = MagicMock()
            mock_function_tool_class.return_value = mock_tool_instance

            result = plugin.use_tool(function)

            assert result is plugin

            call_kwargs = mock_function_tool_class.call_args.kwargs
            assert call_kwargs["name"] == "pydantic_search"
            assert call_kwargs["description"] == "Search with pydantic params"
            assert call_kwargs["parameters"] == SearchParams.model_json_schema()

            mock_mcp_server.add_tool.assert_called_once_with(mock_tool_instance)

    def test_use_tool_with_none_schema(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """Test use_tool with None parameter schema uses empty dict."""

        def no_param_handler(**kwargs):
            return "no params needed"

        function = Function(
            name="no_params",
            description="A function with no parameters",
            parameter_schema=None,
            handler=no_param_handler,
        )

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_function_tool_class:
            mock_tool_instance = MagicMock()
            mock_function_tool_class.return_value = mock_tool_instance

            result = plugin.use_tool(function)

            assert result is plugin

            call_kwargs = mock_function_tool_class.call_args.kwargs
            assert call_kwargs["name"] == "no_params"
            assert call_kwargs["parameters"] == {}

            mock_mcp_server.add_tool.assert_called_once_with(mock_tool_instance)

    def test_use_tool_raises_on_add_tool_failure(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """Test that exceptions from mcp_server.add_tool propagate."""

        def handler(**kwargs):
            return "ok"

        function = Function(name="bad_fn", description="fails", parameter_schema=None, handler=handler)

        mock_mcp_server.add_tool.side_effect = ValueError("add_tool failed")

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool"):
            with pytest.raises(ValueError, match="add_tool failed"):
                plugin.use_tool(function)

    async def test_wrapped_handler_sync_dict_schema(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """wrapped_handler with dict schema passes kwargs directly to the sync handler."""
        received: dict = {}

        def sync_handler(**kwargs):
            received.update(kwargs)
            return "sync result"

        function = Function(name="fn", description="d", parameter_schema={"type": "object"}, handler=sync_handler)

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_ft_class:
            plugin.use_tool(function)
            wrapped_fn = mock_ft_class.call_args.kwargs["fn"]

        result = await wrapped_fn(x=1, y=2)

        assert result == "sync result"
        assert received == {"x": 1, "y": 2}

    async def test_wrapped_handler_async_handler_is_awaited(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """wrapped_handler awaits async handlers."""

        async def async_handler(**kwargs):
            return "async result"

        function = Function(name="fn", description="d", parameter_schema=None, handler=async_handler)

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_ft_class:
            plugin.use_tool(function)
            wrapped_fn = mock_ft_class.call_args.kwargs["fn"]

        result = await wrapped_fn()

        assert result == "async result"

    async def test_wrapped_handler_pydantic_schema_instantiates_model(
        self, plugin: McpServerPlugin, mock_mcp_server: MagicMock
    ):
        """wrapped_handler with a Pydantic class schema instantiates the model before calling the handler."""

        class MyParams(BaseModel):
            x: int
            y: str

        received: dict = {}

        def handler(params: MyParams):
            received["params"] = params
            return "pydantic result"

        function = Function[MyParams](name="fn", description="d", parameter_schema=MyParams, handler=handler)

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_ft_class:
            plugin.use_tool(function)
            wrapped_fn = mock_ft_class.call_args.kwargs["fn"]

        result = await wrapped_fn(x=42, y="hello")

        assert result == "pydantic result"
        assert isinstance(received["params"], MyParams)
        assert received["params"].x == 42
        assert received["params"].y == "hello"

    async def test_wrapped_handler_exception_propagates(self, plugin: McpServerPlugin, mock_mcp_server: MagicMock):
        """wrapped_handler re-raises exceptions from the underlying handler."""

        def failing_handler(**kwargs):
            raise ValueError("handler failed")

        function = Function(name="fn", description="d", parameter_schema=None, handler=failing_handler)

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_ft_class:
            plugin.use_tool(function)
            wrapped_fn = mock_ft_class.call_args.kwargs["fn"]

        with pytest.raises(ValueError, match="handler failed"):
            await wrapped_fn()

    async def test_wrapped_handler_pydantic_validation_error_propagates(self, plugin: McpServerPlugin):
        """wrapped_handler re-raises Pydantic ValidationError when kwargs don't match the model."""

        class StrictParams(BaseModel):
            count: int

        def handler(params: StrictParams):  # noqa: ARG001
            return "ok"

        function = Function[StrictParams](name="fn", description="d", parameter_schema=StrictParams, handler=handler)

        with patch("microsoft_teams.mcpplugin.server_plugin.FunctionTool") as mock_ft_class:
            plugin.use_tool(function)
            wrapped_fn = mock_ft_class.call_args.kwargs["fn"]

        with pytest.raises(ValidationError):
            await wrapped_fn(count="not-an-int")


class TestMcpServerPluginOnStart:
    """Tests for McpServerPlugin.on_start method."""

    @pytest.fixture
    def mock_mcp_server(self):
        return MagicMock()

    @pytest.fixture
    def plugin(self, mock_mcp_server: MagicMock):
        with patch("microsoft_teams.mcpplugin.server_plugin.FastMCP") as mock_fastmcp_class:
            mock_fastmcp_class.return_value = mock_mcp_server
            p = McpServerPlugin(name="test-server", path="/mcp")
        return p

    @pytest.fixture
    def mock_http_server(self):
        server = MagicMock(spec=HttpServer)
        return server

    async def test_on_start_raises_when_not_fastapi_adapter(self, plugin: McpServerPlugin, mock_http_server):
        """Test on_start raises RuntimeError when adapter is not FastAPIAdapter."""
        mock_adapter = MagicMock()  # Not a FastAPIAdapter instance
        mock_http_server.adapter = mock_adapter
        plugin.http_server = mock_http_server

        event = PluginStartEvent(port=3978)

        with pytest.raises(RuntimeError, match="McpServerPlugin requires FastAPIAdapter"):
            await plugin.on_start(event)

        assert plugin._mounted is False

    async def test_on_start_success_mounts_mcp_server(
        self, plugin: McpServerPlugin, mock_mcp_server: MagicMock, mock_http_server
    ):
        """Test on_start successfully mounts MCP server with FastAPIAdapter."""
        mock_fastapi_adapter = MagicMock(spec=FastAPIAdapter)
        mock_fastapi_adapter.lifespans = []
        mock_fastapi_adapter.app = MagicMock()

        mock_http_server.adapter = mock_fastapi_adapter
        plugin.http_server = mock_http_server

        mock_mcp_http_app = MagicMock()
        mock_mcp_http_app.lifespan = MagicMock()
        mock_mcp_server.http_app = MagicMock(return_value=mock_mcp_http_app)

        event = PluginStartEvent(port=3978)

        await plugin.on_start(event)

        mock_mcp_server.http_app.assert_called_once_with(path="/mcp", transport="http")
        assert mock_mcp_http_app.lifespan in mock_fastapi_adapter.lifespans
        mock_fastapi_adapter.app.mount.assert_called_once_with("/", mock_mcp_http_app)
        assert plugin._mounted is True

    async def test_on_start_already_mounted_logs_warning_and_returns(self, plugin: McpServerPlugin, mock_http_server):
        """Test on_start logs warning and returns early if already mounted."""
        plugin._mounted = True
        plugin.http_server = mock_http_server

        event = PluginStartEvent(port=3978)

        with patch("microsoft_teams.mcpplugin.server_plugin.logger") as mock_logger:
            await plugin.on_start(event)
            mock_logger.warning.assert_called_once_with("MCP server already mounted")

        mock_http_server.adapter.assert_not_called()

    async def test_on_start_exception_propagates_and_not_mounted(
        self, plugin: McpServerPlugin, mock_mcp_server: MagicMock, mock_http_server
    ):
        """Test that exceptions during mounting propagate and _mounted stays False."""
        mock_fastapi_adapter = MagicMock(spec=FastAPIAdapter)
        mock_fastapi_adapter.lifespans = []
        mock_fastapi_adapter.app = MagicMock()
        mock_fastapi_adapter.app.mount.side_effect = RuntimeError("mount failed")
        mock_http_server.adapter = mock_fastapi_adapter
        plugin.http_server = mock_http_server

        mock_mcp_http_app = MagicMock()
        mock_mcp_server.http_app = MagicMock(return_value=mock_mcp_http_app)

        event = PluginStartEvent(port=3978)

        with pytest.raises(RuntimeError, match="mount failed"):
            await plugin.on_start(event)

        assert plugin._mounted is False


class TestMcpServerPluginOnStop:
    """Tests for McpServerPlugin.on_stop method."""

    @pytest.fixture
    def plugin(self):
        with patch("microsoft_teams.mcpplugin.server_plugin.FastMCP"):
            p = McpServerPlugin()
        return p

    async def test_on_stop_when_mounted_sets_mounted_false(self, plugin: McpServerPlugin):
        """Test on_stop sets _mounted=False and logs shutdown when mounted."""
        plugin._mounted = True

        with patch("microsoft_teams.mcpplugin.server_plugin.logger") as mock_logger:
            await plugin.on_stop()

        assert plugin._mounted is False
        mock_logger.info.assert_called_once_with("MCP server shutting down")

    async def test_on_stop_when_not_mounted_does_nothing(self, plugin: McpServerPlugin):
        """Test on_stop does nothing when not mounted."""
        plugin._mounted = False

        with patch("microsoft_teams.mcpplugin.server_plugin.logger") as mock_logger:
            await plugin.on_stop()

        assert plugin._mounted is False
        mock_logger.info.assert_not_called()
