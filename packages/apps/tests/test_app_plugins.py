"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""
# pyright: basic

from logging import Logger
from typing import Annotated, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest
from microsoft.teams.api.models.invoke_response import InvokeResponse
from microsoft.teams.apps import (
    DependencyMetadata,
    ErrorEvent,
    EventMetadata,
    LoggerDependencyOptions,
    Plugin,
    PluginBase,
)
from microsoft.teams.apps.app_events import EventManager
from microsoft.teams.apps.app_plugins import PluginProcessor
from microsoft.teams.apps.container import Container
from microsoft.teams.apps.events.types import ActivityEvent
from microsoft.teams.apps.plugins.plugin_activity_event import PluginActivityEvent
from microsoft.teams.common import Client, EventEmitter
from typing_extensions import Any


class TestPluginProcessor:
    """Test cases for PluginProcessor class."""

    @pytest.fixture
    def mock_logger(self):
        return MagicMock(spec=Logger)

    @pytest.fixture
    def container(self):
        return Container()

    @pytest.fixture
    def mock_event_manager(self):
        return MagicMock(spec=EventManager)

    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=Client)

    @pytest.fixture
    def mock_event_emitter(self):
        return MagicMock(spec=EventEmitter)

    @pytest.fixture
    def plugin_processor(self, container, mock_event_emitter, mock_logger, mock_event_manager):
        """Create a PluginProcessor instance."""
        return PluginProcessor(
            container=container,
            event_manager=mock_event_manager,
            event_emitter=mock_event_emitter,
            logger=mock_logger,
        )

    @pytest.fixture
    def mock_plugin(self):
        """Create a test mock plugin."""

        @Plugin(name="MockPlugin", version="1.0", description="A mock plugin for testing")
        class MockPlugin(PluginBase):
            logger: Annotated[Logger, LoggerDependencyOptions()]
            on_error_event: Annotated[Callable[[ErrorEvent], None], EventMetadata(name="error")]
            client: Annotated[Client, DependencyMetadata()]
            on_activity_event: Annotated[Callable[[ActivityEvent], InvokeResponse[Any]], EventMetadata(name="activity")]

            def __init__(self):
                super().__init__()

        return MockPlugin()

    @pytest.mark.asyncio
    async def test_initialize_plugins(self, plugin_processor, mock_plugin):
        """Test the initialize_plugins method."""

        initialized_plugins = plugin_processor.initialize_plugins([mock_plugin])

        assert mock_plugin in initialized_plugins
        assert plugin_processor.get_plugin("MockPlugin") == mock_plugin
        assert plugin_processor.container.MockPlugin() == mock_plugin

    @pytest.mark.asyncio
    async def test_duplicate_in_initialize_plugins(self, plugin_processor, mock_plugin):
        """Test the initialize_plugins method."""

        plugin_processor.initialize_plugins([mock_plugin])

        with pytest.raises(ValueError, match="duplicate plugin MockPlugin found"):
            plugin_processor.initialize_plugins([mock_plugin])

    @pytest.mark.asyncio
    async def test_get_plugin(self, plugin_processor, mock_plugin):
        """Test the get_plugin method."""

        plugin_processor.initialize_plugins([mock_plugin])

        plugin = plugin_processor.get_plugin("MockPlugin")
        assert plugin == mock_plugin

        plugin_none = plugin_processor.get_plugin("NonExistentPlugin")
        assert plugin_none is None

    @pytest.mark.asyncio
    async def test_inject(self, plugin_processor, mock_plugin, mock_logger, mock_client):
        """Test the inject method."""

        plugin_processor.container.set_provider("logger", mock_logger)
        plugin_processor.container.set_provider("client", mock_client)

        invoke_response = InvokeResponse[Any](status=200, body=None)
        plugin_processor.event_manager.on_activity = AsyncMock(return_value=invoke_response)

        plugin_processor.initialize_plugins([mock_plugin])
        plugin_processor.inject(mock_plugin)

        result = await mock_plugin.on_activity_event(MagicMock(spec=PluginActivityEvent))

        assert mock_plugin.logger._extract_mock_name() == "mock().getChild()"
        assert hasattr(mock_plugin, "on_error_event")
        assert mock_plugin.client._extract_mock_name() == "mock()"

        plugin_processor.event_manager.on_activity.assert_called_once()
        assert result == invoke_response
