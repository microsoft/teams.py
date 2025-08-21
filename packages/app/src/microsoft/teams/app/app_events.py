"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import List

from microsoft.teams.common.events.event_emitter import EventEmitter

from .app_process import ActivityProcessor
from .events import ActivityEvent, ActivityResponseEvent, ActivitySentEvent, ErrorEvent, EventType
from .plugins import PluginActivityResponseEvent, PluginActivitySentEvent, PluginBase, PluginErrorEvent, Sender


class EventManager:
    def __init__(self, event_emitter: EventEmitter[EventType], activity_processor: ActivityProcessor):
        self.event_emitter = event_emitter
        self.activity_processor = activity_processor

    async def on_error(self, event: ErrorEvent, plugins: List[PluginBase]) -> None:
        for plugin in plugins:
            if hasattr(plugin, "on_error_event") and callable(plugin.on_error):
                await plugin.on_error(PluginErrorEvent(error=event.error, sender=plugin, activity=event.activity))

        self.event_emitter.emit("error", event)

    async def on_activity(self, event: ActivityEvent, plugins: List[PluginBase]) -> None:
        self.event_emitter.emit("activity", event)
        await self.activity_processor.process_activity(plugins=plugins, sender=event.sender, event=event)

    async def on_activity_sent(self, sender: Sender, event: ActivitySentEvent, plugins: List[PluginBase]) -> None:
        for plugin in plugins:
            if callable(plugin.on_activity_sent):
                await plugin.on_activity_sent(
                    PluginActivitySentEvent(
                        sender=event.sender, activity=event.activity, conversation_ref=event.conversation_ref
                    )
                )
        self.event_emitter.emit("activity_sent", {"event": event, "sender": sender})

    async def on_activity_response(
        self, sender: Sender, event: ActivityResponseEvent, plugins: List[PluginBase]
    ) -> None:
        for plugin in plugins:
            if callable(plugin.on_activity_response):
                await plugin.on_activity_response(
                    PluginActivityResponseEvent(
                        activity=event.activity,
                        sender=sender,
                        response=event.response,
                        conversation_ref=event.conversation_ref,
                    )
                )
        self.event_emitter.emit("activity_response", {"event": event, "sender": sender})
