"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft.teams.app.app import App, AppTokens
from microsoft.teams.app.http_plugin import HttpPlugin
from microsoft.teams.app.options import AppOptions


class TestApp:
    """Test cases for App class public interface."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def mock_storage(self):
        """Create a mock storage."""
        return MagicMock()

    @pytest.fixture
    def mock_activity_handler(self):
        """Create a mock activity handler."""

        async def handler(activity):
            return {"status": "handled", "activityId": activity.get("id")}

        return handler

    @pytest.fixture
    def basic_options(self, mock_logger, mock_storage):
        """Create basic app options."""
        return AppOptions(
            logger=mock_logger,
            storage=mock_storage,
            client_id="test-client-id",
            client_secret="test-secret",
        )

    @pytest.fixture
    def app_with_options(self, basic_options):
        """Create App with basic options."""
        return App(basic_options)

    @pytest.fixture
    def app_with_activity_handler(self, basic_options, mock_activity_handler):
        """Create App with activity handler."""
        basic_options.activity_handler = mock_activity_handler
        return App(basic_options)

    def test_init_default_options(self):
        """Test App initialization with default options."""
        app = App()

        assert app.options is not None
        assert app.log is not None
        assert app.storage is not None
        assert app.http_client is not None
        assert app.api is not None
        assert isinstance(app.tokens, AppTokens)
        assert app.plugins is not None
        assert len(app.plugins) >= 1  # Should have at least HTTP plugin
        assert isinstance(app.http, HttpPlugin)

    def test_init_with_options(self, basic_options):
        """Test App initialization with custom options."""
        app = App(basic_options)

        assert app.options == basic_options
        assert app.log == basic_options.logger
        assert app.storage == basic_options.storage
        assert app.credentials is not None
        assert app.credentials.client_id == "test-client-id"

    def test_init_without_credentials(self):
        """Test App initialization without credentials."""
        app = App(AppOptions())

        assert app.credentials is None

    def test_init_credentials_from_env(self):
        """Test App initialization with credentials from environment."""
        with patch.dict(
            os.environ, {"CLIENT_ID": "env-client-id", "CLIENT_SECRET": "env-secret", "TENANT_ID": "env-tenant"}
        ):
            app = App()

            assert app.credentials is not None
            assert app.credentials.client_id == "env-client-id"
            assert app.credentials.client_secret == "env-secret"
            assert app.credentials.tenant_id == "env-tenant"

    def test_init_options_override_env(self, basic_options):
        """Test that options override environment variables."""
        with patch.dict(os.environ, {"CLIENT_ID": "env-client-id", "CLIENT_SECRET": "env-secret"}):
            app = App(basic_options)

            # Options should override environment
            assert app.credentials.client_id == "test-client-id"

    def test_http_plugin_creation(self, app_with_options):
        """Test that HTTP plugin is created and configured."""
        assert app_with_options.http is not None
        assert isinstance(app_with_options.http, HttpPlugin)
        assert app_with_options.http.activity_handler == app_with_options.handle_activity

    def test_app_id_property_with_bot_token(self, app_with_options):
        """Test app ID property with bot token."""
        mock_bot_token = MagicMock()
        mock_bot_token.app_id = "bot-app-id"
        app_with_options.tokens.bot = mock_bot_token

        assert app_with_options.id == "bot-app-id"

    def test_app_id_property_with_graph_token(self, app_with_options):
        """Test app ID property with graph token."""
        mock_graph_token = MagicMock()
        mock_graph_token.app_id = "graph-app-id"
        app_with_options.tokens.graph = mock_graph_token

        assert app_with_options.id == "graph-app-id"

    def test_app_name_property_no_tokens(self, app_with_options):
        """Test app name property when no tokens are available."""
        assert app_with_options.name is None

    def test_app_name_property_with_bot_token(self, app_with_options):
        """Test app name property with bot token."""
        mock_bot_token = MagicMock()
        mock_bot_token.app_display_name = "Test Bot App"
        app_with_options.tokens.bot = mock_bot_token

        assert app_with_options.name == "Test Bot App"

    @pytest.mark.asyncio
    async def test_start_success(self, app_with_options):
        """Test successful app startup."""
        # Mock the refresh tokens and plugin start methods
        with (
            patch.object(app_with_options, "_refresh_tokens", new_callable=AsyncMock) as mock_refresh,
            patch.object(app_with_options.http, "on_start", new_callable=AsyncMock),
        ):
            start_task = asyncio.create_task(app_with_options.start(3978))

            # Give it a moment to start
            await asyncio.sleep(0.1)

            # Verify state
            assert app_with_options.port == 3978
            assert app_with_options.is_running is True
            mock_refresh.assert_called_once_with(force=True)

            # Cancel the task to prevent it from running indefinitely
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_start_default_port(self, app_with_options):
        """Test app startup with default port."""
        with (
            patch.object(app_with_options, "_refresh_tokens", new_callable=AsyncMock),
            patch.object(app_with_options.http, "on_start", new_callable=AsyncMock),
        ):
            start_task = asyncio.create_task(app_with_options.start())

            await asyncio.sleep(0.1)

            assert app_with_options.port == 3978  # Default port

            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_start_port_from_env(self, app_with_options):
        """Test app startup with port from environment."""
        with (
            patch.dict(os.environ, {"PORT": "8080"}),
            patch.object(app_with_options, "_refresh_tokens", new_callable=AsyncMock),
            patch.object(app_with_options.http, "on_start", new_callable=AsyncMock),
        ):
            start_task = asyncio.create_task(app_with_options.start())

            await asyncio.sleep(0.1)

            assert app_with_options.port == 8080

            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_start_refresh_tokens_failure(self, app_with_options):
        """Test app startup when token refresh fails."""
        with patch.object(
            app_with_options, "_refresh_tokens", new_callable=AsyncMock, side_effect=Exception("Token refresh failed")
        ):
            with pytest.raises(Exception, match="Token refresh failed"):
                await app_with_options.start(3978)

            # App should not be marked as running on failure
            assert app_with_options.is_running is False

    @pytest.mark.asyncio
    async def test_start_plugin_failure(self, app_with_options):
        """Test app startup when plugin start fails."""
        with (
            patch.object(app_with_options, "_refresh_tokens", new_callable=AsyncMock),
            patch.object(
                app_with_options.http, "on_start", new_callable=AsyncMock, side_effect=Exception("Plugin failed")
            ),
        ):
            with pytest.raises(Exception, match="Plugin failed"):
                await app_with_options.start(3978)

            # App should not be marked as running on failure
            assert app_with_options.is_running is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, app_with_options):
        """Test starting app when already running."""
        # Use a mock to simulate app already running by mocking the private attribute
        app_with_options._running = True

        with patch.object(app_with_options, "_refresh_tokens", new_callable=AsyncMock) as mock_refresh:
            await app_with_options.start(3978)

            # Should not try to refresh tokens again
            mock_refresh.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop(self, app_with_options):
        """Test app shutdown."""
        # Set app as running
        app_with_options._running = True

        with patch.object(app_with_options.http, "on_stop", new_callable=AsyncMock) as mock_stop:
            await app_with_options.stop()

            assert app_with_options.is_running is False
            mock_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_not_running(self, app_with_options):
        """Test stopping app when not running."""
        # App is not running by default, so this test should work as-is
        assert app_with_options.is_running is False

        with patch.object(app_with_options.http, "on_stop", new_callable=AsyncMock) as mock_stop:
            await app_with_options.stop()

            # Should not try to stop plugins
            mock_stop.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_plugin_failure(self, app_with_options):
        """Test app shutdown when plugin stop fails."""
        app_with_options._running = True

        with patch.object(
            app_with_options.http, "on_stop", new_callable=AsyncMock, side_effect=Exception("Stop failed")
        ):
            with pytest.raises(Exception, match="Stop failed"):
                await app_with_options.stop()

    @pytest.mark.asyncio
    async def test_handle_activity_success(self, app_with_activity_handler):
        """Test successful activity handling."""
        activity = {"type": "message", "id": "test-activity-id", "text": "Hello, world!"}

        # Mock the HTTP plugin response method
        app_with_activity_handler.http.on_activity_response = MagicMock()

        result = await app_with_activity_handler.handle_activity(activity)

        assert result["status"] == "processed"
        assert result["activityId"] == "test-activity-id"
        app_with_activity_handler.http.on_activity_response.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_activity_no_handler(self, app_with_options):
        """Test activity handling without custom handler."""
        activity = {"type": "message", "id": "test-activity-id", "text": "Hello, world!"}

        app_with_options.http.on_activity_response = MagicMock()

        result = await app_with_options.handle_activity(activity)

        assert result["status"] == "processed"
        assert result["activityId"] == "test-activity-id"

    @pytest.mark.asyncio
    async def test_handle_activity_handler_exception(self, app_with_options):
        """Test activity handling when handler raises exception."""

        async def failing_handler(activity):
            raise ValueError("Handler failed")

        app_with_options.activity_handler = failing_handler
        app_with_options.http.on_error = MagicMock()

        activity = {"type": "message", "id": "test-activity-id", "text": "Hello, world!"}

        # Should handle the exception gracefully
        with pytest.raises(ValueError, match="Handler failed"):
            await app_with_options.handle_activity(activity)

    def test_tokens_property(self, app_with_options):
        """Test tokens property."""
        tokens = app_with_options.tokens
        assert isinstance(tokens, AppTokens)
        assert tokens.bot is None
        assert tokens.graph is None

    def test_plugins_list(self, app_with_options):
        """Test plugins list contains HTTP plugin."""
        assert len(app_with_options.plugins) >= 1
        assert app_with_options.http in app_with_options.plugins
        assert app_with_options.plugins[-1] == app_with_options.http  # HTTP plugin is last
