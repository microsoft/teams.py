"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, List, Optional, cast, get_type_hints

from dependency_injector import providers
from microsoft.teams.common.events.event_emitter import EventEmitter
from microsoft.teams.common.logging.console import ConsoleLogger

from .app_events import EventManager
from .container import Container
from .events import ActivityEvent, ErrorEvent, EventType, is_registered_event
from .plugins import (
    DependencyMetadata,
    EventMetadata,
    PluginActivityEvent,
    PluginBase,
    PluginErrorEvent,
    Sender,
    get_metadata,
)


class PluginManager:
    def __init__(
        self, container: Container, event_manager: EventManager, logger: Logger, event_emitter: EventEmitter[EventType]
    ):
        self.plugins: List[PluginBase] = []
        self.container = container
        self.event_manager = event_manager
        self.logger = logger
        self.event_emitter = event_emitter

    def initialize_plugins(self, plugins: List[PluginBase]) -> List[PluginBase]:
        """Adds a plugin."""

        for plugin in plugins:
            metadata = get_metadata(plugin)

            if metadata is None:
                raise ValueError(f"Plugin {plugin.__class__.__name__} missing metadata")

            name = metadata.name

            if not name:
                raise ValueError(f"Plugin {plugin.__class__.__name__} missing name in metadata")

            if self.get_plugin(name):
                raise ValueError(f"Duplicate plugin {name} found")

            self.plugins.append(plugin)
            self.container.set_provider(name, providers.Object(plugin))

            class_name = plugin.__class__.__name__
            if class_name != name:
                self.container.set_provider(class_name, providers.Object(plugin))

        return self.plugins

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get plugin by name."""
        for plugin in self.plugins:
            metadata = get_metadata(plugin)
            if metadata and metadata.name == name:
                return plugin

    def inject(self, plugin: PluginBase) -> None:
        """Inject dependencies and events into the plugin."""

        hints = get_type_hints(plugin, include_extras=True)

        for field_name, annotated_type in hints.items():
            origin = getattr(annotated_type, "__origin__", None)
            metadata = getattr(annotated_type, "__metadata__", ())

            for meta in metadata:
                if isinstance(meta, EventMetadata):
                    if meta.name == "error":

                        async def error_handler(event: PluginErrorEvent) -> None:
                            await self.event_manager.on_error(
                                ErrorEvent(error=event.error, activity=event.activity, sender=plugin), self.plugins
                            )

                        setattr(plugin, field_name, error_handler)
                    if meta.name == "activity":

                        async def activity_handler(event: PluginActivityEvent) -> None:
                            sender = cast(Sender, plugin)
                            await self.event_manager.on_activity(
                                ActivityEvent(activity=event.activity, sender=sender, token=event.token), self.plugins
                            )

                        setattr(plugin, field_name, activity_handler)
                    elif meta.name == "custom":

                        async def custom_handler(name: str, event: Any) -> None:
                            if is_registered_event(name):
                                self.logger.warning(
                                    f"event {name} is reserved by core app-events but an plugin is trying to emit it"
                                )
                                return
                            self.event_emitter.emit(name, event)

                        setattr(plugin, field_name, custom_handler)
                elif isinstance(meta, DependencyMetadata):
                    dependency = None
                    if origin:
                        dependency = getattr(self.container, origin, None)
                    if not dependency:
                        dependency = getattr(self.container, field_name, None)
                    if not dependency:
                        if not meta.optional:
                            raise ValueError(
                                f"dependency of {origin} of property {field_name} not found "
                                + "but plugin {plugin.__class__.__name__} depends on it"
                            )
                    if field_name == "logger":
                        dependency = cast(ConsoleLogger, dependency)
                        dependency = dependency.get_child(plugin.__class__.__name__)
                    setattr(plugin, field_name, dependency)
