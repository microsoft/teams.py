"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, List, Optional, cast, get_type_hints

from dependency_injector import providers
from microsoft.teams.api.activities import Activity
from microsoft.teams.common.events.event_emitter import EventEmitter

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


class PluginProcessor:
    """
    Processes plugins as apart of the Teams app.

    This class is responsible for initializing plugins, injecting dependencies, and handling events.
    It uses dependency injection to provide plugins with the necessary dependencies and event handlers.
    """

    def __init__(
        self, container: Container, event_manager: EventManager, logger: Logger, event_emitter: EventEmitter[EventType]
    ):
        self.plugins: List[PluginBase] = []
        self.container = container
        self.event_manager = event_manager
        self.logger = logger
        self.event_emitter = event_emitter

    def initialize_plugins(self, plugins: List[PluginBase]) -> List[PluginBase]:
        """Initializes and adds all the plugins for the app."""

        for plugin in plugins:
            metadata = get_metadata(type(plugin))
            name = metadata.name
            class_name = plugin.__class__.__name__

            self.logger.debug(f"Initializing the plugin {class_name}")

            if not name:
                raise ValueError(f"Plugin {class_name} missing name in metadata")

            if self.get_plugin(name):
                raise ValueError(f"duplicate plugin {name} found")

            self.plugins.append(plugin)
            self.container.set_provider(name, providers.Object(plugin))

            if class_name != name:
                self.container.set_provider(class_name, providers.Object(plugin))

        self.logger.info("Successfully initialized all plugins")
        return self.plugins

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Gets the plugin by name."""
        for plugin in self.plugins:
            metadata = get_metadata(type(plugin))
            if metadata.name == name:
                return plugin

    def inject(self, plugin: PluginBase) -> None:
        """Injects dependencies and events into the plugin."""

        hints = get_type_hints(plugin, include_extras=True)

        for field_name, annotated_type in hints.items():
            origin = getattr(annotated_type, "__origin__", None)
            metadata = getattr(annotated_type, "__metadata__", ())

            for meta in metadata:
                self.logger.debug(f"Initializing the dependency {field_name} for {plugin.__class__.__name__}")
                if isinstance(meta, EventMetadata):
                    self._inject_event(meta, plugin, field_name)

                elif isinstance(meta, DependencyMetadata):
                    self._inject_dependency(meta, plugin, origin, field_name)

    def _inject_event(self, meta: EventMetadata, plugin: PluginBase, field_name: str) -> None:
        """Injects event handler into the plugin based on metadata info."""
        if meta.name == "error":
            self.logger.debug("Injecting the error event")

            async def error_handler(event: PluginErrorEvent) -> None:
                activity = cast(Activity, event.activity)
                await self.event_manager.on_error(
                    ErrorEvent(error=event.error, activity=activity, sender=plugin), self.plugins
                )

            setattr(plugin, field_name, error_handler)
        elif meta.name == "activity":
            self.logger.debug("Injecting the activity event")

            async def activity_handler(event: PluginActivityEvent) -> None:
                sender = cast(Sender, plugin)
                await self.event_manager.on_activity(
                    ActivityEvent(activity=event.activity, sender=sender, token=event.token), self.plugins
                )

            setattr(plugin, field_name, activity_handler)
        elif meta.name == "custom":
            self.logger.debug("Injecting the custom event")

            async def custom_handler(name: str, event: Any) -> None:
                if is_registered_event(name):
                    self.logger.warning(
                        f"event {name} is reserved by core app-events but an plugin is trying to emit it"
                    )
                    return
                self.event_emitter.emit(name, event)

            setattr(plugin, field_name, custom_handler)

    def _inject_dependency(self, meta: DependencyMetadata, plugin: PluginBase, type_name: Any, field_name: str) -> None:
        """Injects dependency into the plugin based on metadata info."""
        dependency = None

        if type_name:
            dependency = getattr(self.container, type_name.__name__, None)
        if not dependency:
            dependency = getattr(self.container, field_name, None)
        if not dependency:
            if not meta.optional:
                raise ValueError(
                    f"dependency of {type_name} of property {field_name} not found "
                    + f"but plugin {plugin.__class__.__name__} depends on it"
                )
        else:
            # Calling the provider to get the actual instance
            dependency = dependency()
            if field_name == "logger":
                logger_dependency = cast(Logger, dependency)
                dependency = logger_dependency.getChild(plugin.__class__.__name__)
            setattr(plugin, field_name, dependency)
            self.logger.debug(f"Successfully injected the dependency {field_name} into {plugin.__class__.__name__}")
