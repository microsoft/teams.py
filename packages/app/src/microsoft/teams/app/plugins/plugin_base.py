"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from microsoft.teams.api.activities import ActivityParams, SentActivity
from microsoft.teams.api.models.conversation import ConversationReference

from .plugin_activity_event import PluginActivityEvent
from .plugin_activity_response_event import PluginActivityResponseEvent
from .plugin_activity_sent_event import PluginActivitySentEvent
from .plugin_error_event import PluginErrorEvent
from .plugin_start_event import PluginStartEvent
from .streamer import StreamerProtocol


class PluginBase:
    """The base plugin for Teams app plugins."""

    async def on_init(self) -> None:
        """Lifecycle method called by the App when the plugin is initialized."""
        ...

    async def on_start(self, event: PluginStartEvent) -> None:
        """Lifecycle method called by the App when the plugin is started."""
        ...

    async def on_stop(self) -> None:
        """Lifecycle method called by the App once during shutdown."""
        ...

    async def on_error(self, event: PluginErrorEvent) -> None:
        """Called by the App when an error occurs."""
        ...

    async def on_activity(self, event: PluginActivityEvent) -> None:
        """Called by the App when an activity is received."""
        ...

    async def on_activity_sent(self, event: PluginActivitySentEvent) -> None:
        """Called by the App when an activity is sent"""
        ...

    async def on_activity_response(self, event: PluginActivityResponseEvent) -> None:
        """Called by the App when an activity response is sent."""
        ...

    async def send(self, activity: ActivityParams, ref: ConversationReference) -> SentActivity:
        """Called by the App to send an activity"""
        ...

    async def create_stream(self, ref: ConversationReference) -> StreamerProtocol:
        """Called by the App to create a new activity stream"""
        ...
