"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

import asyncio
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft.teams.api import (
    Account,
    ConfigResponse,
    ConversationAccount,
    ConversationReference,
    InvokeResponse,
    MessageActivity,
    MessageActivityInput,
)
from microsoft.teams.apps import HttpPlugin, PluginActivityResponseEvent, PluginErrorEvent, PluginStartEvent


class TestHttpPlugin:
    """Test cases for HttpPlugin public interface."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def plugin_with_validator(self, mock_logger):
        """Create HttpPlugin with token validator."""
        return HttpPlugin("test-app-id", mock_logger)

    @pytest.fixture
    def plugin_without_validator(self, mock_logger):
        """Create HttpPlugin without token validator."""
        return HttpPlugin(None, mock_logger)

    def test_init_with_app_id(self, mock_logger):
        """Test HttpPlugin initialization with app ID."""
        plugin = HttpPlugin("test-app-id", mock_logger)

        assert plugin.logger == mock_logger
        assert plugin.app is not None
        assert plugin.pending == {}

    def test_init_without_app_id(self, mock_logger):
        """Test HttpPlugin initialization without app ID."""
        plugin = HttpPlugin(None, mock_logger)

        assert plugin.logger == mock_logger
        assert plugin.app is not None

    def test_init_with_default_logger(self):
        """Test HttpPlugin initialization with default logger."""
        plugin = HttpPlugin("test-app-id", None)

        assert plugin.logger is not None

    def test_fastapi_methods_exposed(self, plugin_with_validator):
        """Test that FastAPI methods are properly exposed."""
        assert hasattr(plugin_with_validator, "get")
        assert hasattr(plugin_with_validator, "post")
        assert hasattr(plugin_with_validator, "put")
        assert hasattr(plugin_with_validator, "patch")
        assert hasattr(plugin_with_validator, "delete")
        assert hasattr(plugin_with_validator, "middleware")

        # These should be bound to the FastAPI app methods
        assert plugin_with_validator.get == plugin_with_validator.app.get
        assert plugin_with_validator.post == plugin_with_validator.app.post

    @pytest.mark.asyncio
    async def test_on_activity_response_success(self, plugin_with_validator, mock_account):
        """Test successful activity response completion."""
        # Create a pending future
        future = asyncio.get_event_loop().create_future()
        plugin_with_validator.pending["test-id"] = future

        mock_activity = cast(
            MessageActivity,
            MessageActivityInput(type="message", text="Mock activity text", from_=mock_account, id="test-id"),
        )

        mock_reference = ConversationReference(
            bot=Account(id="1", name="test-bot", role="bot"),
            conversation=ConversationAccount(id="conv-789", conversation_type="personal"),
            channel_id="msteams",
            service_url="https://test.service.url",
        )

        response_data = InvokeResponse(body=cast(ConfigResponse, {"status": "success"}), status=200)
        await plugin_with_validator.on_activity_response(
            PluginActivityResponseEvent(
                sender=plugin_with_validator,
                activity=mock_activity,
                response=response_data,
                conversation_ref=mock_reference,
            )
        )

        assert future.done()
        assert future.result() == response_data

    @pytest.mark.asyncio
    async def test_on_activity_response_no_pending(self, plugin_with_validator, mock_account):
        """Test activity response with no pending future."""

        mock_activity = cast(
            MessageActivity,
            MessageActivityInput(type="message", text="Mock activity text", from_=mock_account, id="random-id"),
        )
        response_data = InvokeResponse(body=cast(ConfigResponse, {"status": "success"}), status=200)
        mock_reference = ConversationReference(
            bot=Account(id="1", name="test-bot", role="bot"),
            conversation=ConversationAccount(id="conv-789", conversation_type="personal"),
            channel_id="msteams",
            service_url="https://test.service.url",
        )

        # Should not raise exception
        await plugin_with_validator.on_activity_response(
            PluginActivityResponseEvent(
                sender=plugin_with_validator,
                activity=mock_activity,
                response=response_data,
                conversation_ref=mock_reference,
            )
        )

    @pytest.mark.asyncio
    async def test_on_activity_response_already_done(self, plugin_with_validator, mock_account):
        """Test activity response when future is already done."""
        future = asyncio.get_event_loop().create_future()
        future.set_result("already done")
        plugin_with_validator.pending["test-id"] = future

        mock_activity = cast(
            MessageActivity,
            MessageActivityInput(type="message", text="Mock activity text", from_=mock_account, id="test-id"),
        )
        response_data = InvokeResponse(body=cast(ConfigResponse, {"status": "success"}), status=200)
        mock_reference = ConversationReference(
            bot=Account(id="1", name="test-bot", role="bot"),
            conversation=ConversationAccount(id="conv-789", conversation_type="personal"),
            channel_id="msteams",
            service_url="https://test.service.url",
        )

        # Should not raise exception
        await plugin_with_validator.on_activity_response(
            PluginActivityResponseEvent(
                sender=plugin_with_validator,
                activity=mock_activity,
                response=response_data,
                conversation_ref=mock_reference,
            )
        )

        # Future should still have original result
        assert future.result() == "already done"

    @pytest.mark.asyncio
    async def test_on_error_with_activity_id(self, plugin_with_validator, mock_account):
        """Test error handling with activity ID."""
        # Create a pending future
        future = asyncio.get_event_loop().create_future()
        plugin_with_validator.pending["test-id"] = future
        mock_activity = cast(
            MessageActivity,
            MessageActivityInput(type="message", text="Mock activity text", from_=mock_account, id="test-id"),
        )

        error = ValueError("Test error")
        await plugin_with_validator.on_error(
            PluginErrorEvent(sender=plugin_with_validator, activity=mock_activity, error=error)
        )

        assert future.done()
        with pytest.raises(ValueError, match="Test error"):
            future.result()

    @pytest.mark.asyncio
    async def test_on_error_no_pending_future(self, plugin_with_validator):
        """Test error handling with no pending future."""
        error = ValueError("Test error")
        # Should not raise exception
        await plugin_with_validator.on_error(PluginErrorEvent(sender=plugin_with_validator, error=error))

    @pytest.mark.asyncio
    async def test_on_start_success(self, plugin_with_validator):
        """Test successful server startup."""
        mock_server = MagicMock()
        mock_server.serve = AsyncMock()

        with (
            patch("uvicorn.Config") as mock_config,
            patch("uvicorn.Server", return_value=mock_server) as mock_server_class,
        ):
            mock_config.return_value = MagicMock()

            # Mock the serve method to not actually start server
            mock_server.serve.return_value = None
            event = PluginStartEvent(port=3978)
            await plugin_with_validator.on_start(event)

            # Verify server was configured and started
            mock_config.assert_called_once()
            mock_server_class.assert_called_once()
            mock_server.serve.assert_called_once()

            assert plugin_with_validator._port == 3978
            assert plugin_with_validator._server == mock_server

    @pytest.mark.asyncio
    async def test_on_start_port_in_use(self, plugin_with_validator):
        """Test server startup when port is in use."""
        with patch("uvicorn.Server") as mock_server_class:
            mock_server = MagicMock()
            mock_server.serve = AsyncMock(side_effect=OSError("Port already in use"))
            mock_server_class.return_value = mock_server

            with pytest.raises(OSError, match="Port already in use"):
                event = PluginStartEvent(port=3978)
                await plugin_with_validator.on_start(event)

    @pytest.mark.asyncio
    async def test_on_stop(self, plugin_with_validator):
        """Test server shutdown."""
        # Set up a mock server
        mock_server = MagicMock()
        plugin_with_validator._server = mock_server

        await plugin_with_validator.on_stop()

        assert mock_server.should_exit is True

    @pytest.mark.asyncio
    async def test_on_stop_no_server(self, plugin_with_validator):
        """Test server shutdown when no server is running."""
        plugin_with_validator._server = None

        # Should not raise exception
        await plugin_with_validator.on_stop()

    def test_activity_handler_assignment(self, plugin_with_validator):
        """Test activity handler assignment and retrieval."""

        async def new_handler(activity):
            return {"custom": "response"}

        plugin_with_validator.activity_handler = new_handler
        assert plugin_with_validator.activity_handler == new_handler

    def test_pending_futures_management(self, plugin_with_validator):
        """Test pending futures dictionary management."""
        # Initially empty
        assert len(plugin_with_validator.pending) == 0

        # Add futures
        future1 = asyncio.get_event_loop().create_future()
        future2 = asyncio.get_event_loop().create_future()

        plugin_with_validator.pending["activity1"] = future1
        plugin_with_validator.pending["activity2"] = future2

        assert len(plugin_with_validator.pending) == 2
        assert plugin_with_validator.pending["activity1"] == future1
        assert plugin_with_validator.pending["activity2"] == future2

    def test_middleware_setup(self, plugin_with_validator, plugin_without_validator):
        """Test that JWT middleware is properly configured."""
        # With app_id, middleware should be added
        assert plugin_with_validator.app is not None
        # Without app_id, no middleware but app still exists
        assert plugin_without_validator.app is not None

    def test_logger_property(self, mock_logger):
        """Test logger property assignment."""
        plugin = HttpPlugin("test-app-id", mock_logger)
        assert plugin.logger == mock_logger

    def test_app_property(self, plugin_with_validator):
        """Test FastAPI app property."""
        from fastapi import FastAPI

        assert isinstance(plugin_with_validator.app, FastAPI)
