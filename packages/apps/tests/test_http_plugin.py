"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, Response
from microsoft_teams.api import (
    Account,
    ConfigResponse,
    ConversationAccount,
    ConversationReference,
    InvokeResponse,
    MessageActivity,
    MessageActivityInput,
)
from microsoft_teams.apps import HttpPlugin, PluginActivityResponseEvent, PluginErrorEvent, PluginStartEvent
from microsoft_teams.apps.events import ActivityEvent


class TestHttpPlugin:
    """Test cases for HttpPlugin public interface."""

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return MagicMock()

    @pytest.fixture
    def plugin_with_validator(self, mock_logger):
        """Create HttpPlugin with token validator."""
        return HttpPlugin(logger=mock_logger)

    @pytest.fixture
    def plugin_without_validator(self, mock_logger):
        """Create HttpPlugin without token validator."""
        return HttpPlugin(logger=mock_logger)

    def test_init_with_default_logger(self):
        """Test HttpPlugin initialization with default logger."""
        plugin = HttpPlugin()

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
    async def test_on_activity_response(self, plugin_without_validator, mock_account, mock_logger):
        """Test successful activity response completion."""
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
        await plugin_without_validator.on_activity_response(
            PluginActivityResponseEvent(
                sender=plugin_without_validator,
                activity=mock_activity,
                response=response_data,
                conversation_ref=mock_reference,
            )
        )

        mock_logger.debug.assert_called_once()
        mock_logger.debug.assert_called_with(f"Completing activity response for {mock_activity.id}")

    @pytest.mark.asyncio
    async def test_on_error(self, plugin_with_validator, mock_account, mock_logger):
        """Test error handling with activity ID."""
        mock_activity = cast(
            MessageActivity,
            MessageActivityInput(type="message", text="Mock activity text", from_=mock_account, id="test-id"),
        )

        error = ValueError("Test error")
        await plugin_with_validator.on_error(
            PluginErrorEvent(sender=plugin_with_validator, activity=mock_activity, error=error)
        )

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

    def test_middleware_setup(self, plugin_with_validator, plugin_without_validator):
        """Test that JWT middleware is properly configured."""
        # With app_id, middleware should be added
        assert plugin_with_validator.app is not None
        # Without app_id, no middleware but app still exists
        assert plugin_without_validator.app is not None

    def test_logger_property(self, mock_logger):
        """Test logger property assignment."""
        plugin = HttpPlugin(logger=mock_logger)
        assert plugin.logger == mock_logger

    def test_app_property(self, plugin_with_validator):
        """Test FastAPI app property."""
        from fastapi import FastAPI

        assert isinstance(plugin_with_validator.app, FastAPI)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("is_handler_async", [True, False])
    async def test_on_activity_request_success(self, plugin_without_validator, mock_account, is_handler_async):
        """Test on_activity_request with successful async/sync on_activity_event handler."""
        expected_body = {"status": "success"}
        expected_response = InvokeResponse(body=cast(ConfigResponse, expected_body), status=200)
        mock_handler = (
            AsyncMock(return_value=expected_response) if is_handler_async else MagicMock(return_value=expected_response)
        )
        plugin_without_validator.on_activity_event = mock_handler

        mock_request = AsyncMock(spec=Request)
        activity = cast(
            MessageActivity,
            MessageActivityInput(
                type="message",
                text="Test message",
                from_=mock_account,
                id="test-123",
                channel_id="msteams",
                conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
                recipient=mock_account,
            ),
        )
        mock_request.json.return_value = activity.model_dump()
        mock_request.state = MagicMock()
        mock_request.state.validated_token = None

        mock_response = MagicMock(spec=Response)

        result = await plugin_without_validator.on_activity_request(mock_request, mock_response)

        mock_handler.assert_called_once()
        call_args = mock_handler.call_args[0][0]
        assert isinstance(call_args, ActivityEvent)
        assert call_args.sender == plugin_without_validator

        assert result == expected_body

    @pytest.mark.asyncio
    @pytest.mark.parametrize("is_handler_async", [True, False])
    async def test_on_activity_request_exception(self, plugin_without_validator, mock_account, is_handler_async):
        """Test on_activity_request when handler raises exception."""
        test_error = ValueError("Handler failed")
        mock_handler = AsyncMock(side_effect=test_error) if is_handler_async else MagicMock(side_effect=test_error)
        plugin_without_validator.on_activity_event = mock_handler

        mock_request = AsyncMock(spec=Request)
        activity = cast(
            MessageActivity,
            MessageActivityInput(
                type="message",
                text="Test message",
                from_=mock_account,
                id="test-123",
                channel_id="msteams",
                conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
                recipient=mock_account,
            ),
        )
        mock_request.json.return_value = activity.model_dump()
        mock_request.state = MagicMock()
        mock_request.state.validated_token = None

        mock_response = MagicMock(spec=Response)

        result = await plugin_without_validator.on_activity_request(mock_request, mock_response)

        mock_handler.assert_called_once()
        # Exception is logged directly at exception site
        plugin_without_validator.logger.exception.assert_called_once_with(str(test_error))

        assert isinstance(result, Response)
        assert result.status_code == 500

    # Tests for HttpPlugin.send() with targeted messages

    @pytest.fixture
    def plugin_for_send(self):
        """Create HttpPlugin for send testing."""
        plugin = HttpPlugin(logger=MagicMock())
        plugin.client = MagicMock()
        plugin.client.clone = MagicMock(return_value=MagicMock())
        plugin.bot_token = MagicMock()
        return plugin

    @pytest.fixture
    def conversation_ref(self):
        """Create a conversation reference for testing."""
        return ConversationReference(
            bot=Account(id="bot-123", name="Test Bot", role="bot"),
            conversation=ConversationAccount(id="conv-456", conversation_type="personal"),
            channel_id="msteams",
            service_url="https://test.service.url",
        )

    def _create_sent_activity(self, activity, activity_id="msg-123"):
        """Helper to create a proper SentActivity mock."""
        from microsoft_teams.api import SentActivity

        return SentActivity(id=activity_id, activity_params=activity)

    @pytest.mark.asyncio
    async def test_send_non_targeted_message_calls_create(self, plugin_for_send, conversation_ref):
        """Test that non-targeted messages use the regular create method."""
        activity = MessageActivityInput(text="Hello")

        mock_activities = MagicMock()
        mock_activities.create = AsyncMock(return_value=self._create_sent_activity(activity))

        with patch("microsoft_teams.apps.http_plugin.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await plugin_for_send.send(activity, conversation_ref)

            mock_activities.create.assert_called_once_with(activity)
            mock_activities.create_targeted.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_targeted_message_calls_create_targeted(self, plugin_for_send, conversation_ref):
        """Test that targeted messages use the create_targeted method."""

        recipient = Account(id="user-123", name="Test User", role="user")
        activity = MessageActivityInput(text="Hello").with_recipient(recipient, is_targeted=True)

        mock_activities = MagicMock()
        mock_activities.create_targeted = AsyncMock(return_value=self._create_sent_activity(activity))

        with patch("microsoft_teams.apps.http_plugin.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await plugin_for_send.send(activity, conversation_ref)

            mock_activities.create_targeted.assert_called_once_with(activity)
            mock_activities.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_non_targeted_message_calls_update(self, plugin_for_send, conversation_ref):
        """Test that non-targeted message updates use the regular update method."""
        activity = MessageActivityInput(text="Updated message")
        activity.id = "existing-msg-id"

        mock_activities = MagicMock()
        mock_activities.update = AsyncMock(return_value=self._create_sent_activity(activity, "existing-msg-id"))

        with patch("microsoft_teams.apps.http_plugin.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await plugin_for_send.send(activity, conversation_ref)

            mock_activities.update.assert_called_once_with("existing-msg-id", activity)
            mock_activities.update_targeted.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_targeted_message_calls_update_targeted(self, plugin_for_send, conversation_ref):
        """Test that targeted message updates use the update_targeted method."""
        activity = MessageActivityInput(text="Updated targeted message")
        activity.id = "existing-msg-id"
        activity.is_targeted = True

        mock_activities = MagicMock()
        mock_activities.update_targeted = AsyncMock(
            return_value=self._create_sent_activity(activity, "existing-msg-id")
        )

        with patch("microsoft_teams.apps.http_plugin.ApiClient") as mock_api_client:
            mock_api = MagicMock()
            mock_api.conversations.activities.return_value = mock_activities
            mock_api_client.return_value = mock_api

            await plugin_for_send.send(activity, conversation_ref)

            mock_activities.update_targeted.assert_called_once_with("existing-msg-id", activity)
            mock_activities.update.assert_not_called()
