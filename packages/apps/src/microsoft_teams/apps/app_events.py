"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List

from microsoft_teams.common import EventEmitter

from .events import ActivityEvent, ActivityResponseEvent, ActivitySentEvent, ErrorEvent, EventType
from .plugins import PluginActivityResponseEvent, PluginActivitySentEvent, PluginBase, PluginErrorEvent


class EventManager:
    def __init__(self, event_emitter: EventEmitter[EventType]):
        self.event_emitter = event_emitter

    async def on_error(self, event: ErrorEvent, plugins: List[PluginBase]) -> None:
        for plugin in plugins:
            if hasattr(plugin, "on_error_event") and callable(plugin.on_error):
                await plugin.on_error(PluginErrorEvent(error=event.error, activity=event.activity))

        self.event_emitter.emit("error", event)

    async def on_activity(self, event: ActivityEvent) -> None:
        self.event_emitter.emit("activity", event)

    async def on_activity_sent(self, event: ActivitySentEvent, plugins: List[PluginBase]) -> None:
        for plugin in plugins:
            if callable(plugin.on_activity_sent):
                await plugin.on_activity_sent(
                    PluginActivitySentEvent(activity=event.activity, conversation_ref=event.conversation_ref)
                )
        self.event_emitter.emit("activity_sent", event)

    async def on_activity_response(self, event: ActivityResponseEvent, plugins: List[PluginBase]) -> None:
        for plugin in plugins:
            if callable(plugin.on_activity_response):
                await plugin.on_activity_response(
                    PluginActivityResponseEvent(
                        activity=event.activity,
                        response=event.response,
                        conversation_ref=event.conversation_ref,
                    )
                )
        self.event_emitter.emit("activity_response", event)
