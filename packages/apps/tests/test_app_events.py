"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.api import Activity, ConversationReference, TokenProtocol
from microsoft.teams.apps import ActivityEvent, ActivityResponseEvent, ActivitySentEvent, ErrorEvent, HttpPlugin, Sender
from microsoft.teams.apps.app_events import EventManager
from microsoft.teams.apps.app_process import ActivityProcessor
from microsoft.teams.common.events.event_emitter import EventEmitter


class TestEventManager:
    """Test cases for the EventManager class."""

    @pytest.fixture
    def mock_event_emitter(self):
        """Create a mock EventEmitter."""
        return MagicMock(spec=EventEmitter)

    @pytest.fixture
    def mock_activity_processor(self):
        """Create a mock ActivityProcessor."""
        return MagicMock(spec=ActivityProcessor)

    @pytest.fixture
    def event_manager(self, mock_event_emitter, mock_activity_processor):
        """Create an EventManager instance."""
        return EventManager(mock_event_emitter, mock_activity_processor)

    @pytest.fixture
    def mock_plugins(self):
        plugin = MagicMock(spec=HttpPlugin)
        plugin.on_error_event = AsyncMock()
        plugin.on_error = AsyncMock()
        plugin.on_activity_sent = AsyncMock()
        plugin.on_activity_response = AsyncMock()
        plugin_two = MagicMock(spec=HttpPlugin)
        return [plugin, plugin_two]

    @pytest.mark.asyncio
    async def test_on_error(self, event_manager, mock_event_emitter, mock_plugins):
        error_event = ErrorEvent(error=Exception("Test Error"))

        await event_manager.on_error(error_event, mock_plugins)

        for plugin in mock_plugins:
            if hasattr(plugin, "on_error_event"):
                plugin.on_error.assert_called()
        mock_event_emitter.emit.assert_called_once_with("error", error_event)

    @pytest.mark.asyncio
    async def test_on_activity(self, event_manager, mock_event_emitter, mock_activity_processor, mock_plugins):
        """Test the on_activity method."""
        activity_event = ActivityEvent(
            sender=Sender(), activity=MagicMock(spec=Activity), token=MagicMock(spec=TokenProtocol)
        )

        await event_manager.on_activity(activity_event, mock_plugins)

        mock_event_emitter.emit.assert_called_once_with("activity", activity_event)
        mock_activity_processor.process_activity.assert_called_once_with(
            plugins=mock_plugins, sender=activity_event.sender, event=activity_event
        )

    @pytest.mark.asyncio
    async def test_on_activity_sent(self, event_manager, mock_event_emitter, mock_plugins):
        """Test the on_activity_sent method."""
        sender = Sender()
        activity_sent_event = ActivitySentEvent(
            sender=sender, activity=MagicMock(spec=Activity), conversation_ref=MagicMock(spec=ConversationReference)
        )

        await event_manager.on_activity_sent(sender, activity_sent_event, mock_plugins)

        for plugin in mock_plugins:
            if callable(plugin.on_activity_sent):
                plugin.on_activity_sent.assert_called()
        mock_event_emitter.emit.assert_called_once_with(
            "activity_sent", {"event": activity_sent_event, "sender": sender}
        )

    @pytest.mark.asyncio
    async def test_on_activity_response(self, event_manager, mock_event_emitter, mock_plugins):
        """Test the on_activity_response method."""
        sender = Sender()
        activity_response_event = ActivityResponseEvent(
            activity=MagicMock(spec=Activity), response=MagicMock(), conversation_ref=MagicMock()
        )

        await event_manager.on_activity_response(sender, activity_response_event, mock_plugins)

        for plugin in mock_plugins:
            if callable(plugin.on_activity_response):
                plugin.on_activity_response.assert_called()
        mock_event_emitter.emit.assert_called_once_with(
            "activity_response", {"event": activity_response_event, "sender": sender}
        )
