"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from microsoft_teams.api import Activity, ConversationReference, SentActivity, TokenProtocol
from microsoft_teams.apps import (
    ActivityEvent,
    ActivityResponseEvent,
    ActivitySentEvent,
    ErrorEvent,
    PluginBase,
)
from microsoft_teams.apps.app_events import EventManager
from microsoft_teams.apps.events import CoreActivity
from microsoft_teams.apps.events.registry import get_event_name_from_type, get_event_type_from_signature
from microsoft_teams.common import EventEmitter


class TestEventManager:
    """Test cases for the EventManager class."""

    @pytest.fixture
    def mock_event_emitter(self):
        """Create a mock EventEmitter."""
        return MagicMock(spec=EventEmitter)

    @pytest.fixture
    def event_manager(self, mock_event_emitter):
        """Create an EventManager instance."""
        return EventManager(mock_event_emitter)

    @pytest.fixture
    def mock_plugins(self):
        plugin = MagicMock(spec=PluginBase)
        plugin.on_error_event = AsyncMock()
        plugin.on_error = AsyncMock()
        plugin.on_activity_sent = AsyncMock()
        plugin.on_activity_response = AsyncMock()
        plugin_two = MagicMock(spec=PluginBase)
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
    async def test_on_activity(self, event_manager, mock_event_emitter):
        """Test the on_activity method."""
        activity_event = ActivityEvent(body=CoreActivity(), token=MagicMock(spec=TokenProtocol))

        await event_manager.on_activity(activity_event)

        mock_event_emitter.emit.assert_called_once_with("activity", activity_event)

    @pytest.mark.asyncio
    async def test_on_activity_sent(self, event_manager, mock_event_emitter, mock_plugins):
        """Test the on_activity_sent method."""
        activity_sent_event = ActivitySentEvent(
            activity=MagicMock(spec=SentActivity), conversation_ref=MagicMock(spec=ConversationReference)
        )

        await event_manager.on_activity_sent(activity_sent_event, mock_plugins)

        for plugin in mock_plugins:
            if callable(plugin.on_activity_sent):
                plugin.on_activity_sent.assert_called()
        mock_event_emitter.emit.assert_called_once_with("activity_sent", activity_sent_event)

    @pytest.mark.asyncio
    async def test_on_activity_response(self, event_manager, mock_event_emitter, mock_plugins):
        """Test the on_activity_response method."""
        activity_response_event = ActivityResponseEvent(
            activity=MagicMock(spec=Activity), response=MagicMock(), conversation_ref=MagicMock()
        )

        await event_manager.on_activity_response(activity_response_event, mock_plugins)

        for plugin in mock_plugins:
            if callable(plugin.on_activity_response):
                plugin.on_activity_response.assert_called()
        mock_event_emitter.emit.assert_called_once_with("activity_response", activity_response_event)


class TestGetEventNameFromType:
    """Test cases for the get_event_name_from_type function."""

    def test_registered_class_returns_event_name(self):
        """Test that a registered event class returns the correct event name."""
        assert get_event_name_from_type(ActivityEvent) == "activity"
        assert get_event_name_from_type(ErrorEvent) == "error"
        assert get_event_name_from_type(ActivityResponseEvent) == "activity_response"
        assert get_event_name_from_type(ActivitySentEvent) == "activity_sent"

    def test_unregistered_class_raises_value_error(self):
        """Test that an unregistered class raises ValueError."""

        class UnregisteredEvent:
            pass

        with pytest.raises(ValueError, match="UnregisteredEvent"):
            get_event_name_from_type(UnregisteredEvent)


class TestGetEventTypeFromSignature:
    """Test cases for the get_event_type_from_signature function."""

    def test_function_with_no_parameters_returns_none(self):
        """Test that a function with no parameters returns None."""

        def no_params():
            pass

        result = get_event_type_from_signature(no_params)
        assert result is None

    def test_function_with_no_annotation_returns_none(self):
        """Test that a function where the first param has no annotation returns None."""

        def no_annotation(event):
            pass

        result = get_event_type_from_signature(no_annotation)
        assert result is None

    def test_function_with_registered_type_returns_event_name(self):
        """Test that a function typed with a registered event class returns the event name."""

        def handler(event: ActivityEvent):
            pass

        result = get_event_type_from_signature(handler)
        assert result == "activity"

    def test_function_with_string_annotation_matching_event_name(self):
        """Test that a string annotation matching a registered event name returns it."""

        # Build a function whose annotation is already a bare string equal to an event name.
        # We create the parameter manually to guarantee a string annotation.
        def handler(event):
            pass

        # Patch the annotation directly so it is the string "activity"
        handler.__annotations__["event"] = "activity"

        result = get_event_type_from_signature(handler)
        assert result == "activity"

    def test_function_with_string_annotation_matching_class_name(self):
        """Test that a string annotation matching a registered class name resolves correctly."""

        def handler(event):
            pass

        # "ActivityEvent" is the class name — triggers the class-name fallback path
        handler.__annotations__["event"] = "ActivityEvent"

        result = get_event_type_from_signature(handler)
        assert result == "activity"

    def test_function_with_unregistered_string_annotation_returns_none(self):
        """Test that a string annotation that doesn't match anything returns None."""

        def handler(event):
            pass

        handler.__annotations__["event"] = "UnknownEventType"

        result = get_event_type_from_signature(handler)
        assert result is None

    def test_function_with_unregistered_type_returns_none(self):
        """Test that a function typed with an unregistered type returns None."""

        class SomeRandomClass:
            pass

        def handler(event: SomeRandomClass):
            pass

        result = get_event_type_from_signature(handler)
        assert result is None

    def test_function_raising_type_error_returns_none(self):
        """Test that when inspect.signature raises TypeError, get_event_type_from_signature returns None."""
        with patch("inspect.signature", side_effect=TypeError):
            result = get_event_type_from_signature(lambda x: x)
        assert result is None
