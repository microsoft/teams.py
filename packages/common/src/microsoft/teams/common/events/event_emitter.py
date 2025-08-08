"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, Generic, List, Optional, Protocol, TypedDict, TypeVar, Union

from ..logging import ConsoleLogger

EventTypeT = TypeVar("EventTypeT", bound=str, contravariant=True)

EventHandler = Union[
    Callable[[Any], None],  # Sync handler
    Callable[[Any], Awaitable[Any]],  # Async handler
]


class Subscription(TypedDict):
    """A subscription entry for an event handler."""

    id: int
    handler: EventHandler


class EventEmitterProtocol(Protocol, Generic[EventTypeT]):
    """Interface for event emitter functionality."""

    def on(self, event: EventTypeT, handler: EventHandler) -> int:
        """Register an event handler. Returns subscription ID."""
        ...

    def once(self, event: EventTypeT, handler: EventHandler) -> int:
        """Register a one-time event handler. Returns subscription ID."""
        ...

    def off(self, subscription_id: int) -> None:
        """Remove an event handler by subscription ID."""

    def emit(self, event: EventTypeT, value: Any = None) -> None:
        """Emit an event synchronously."""


class EventEmitterOptions(TypedDict, total=False):
    """
    Options for EventEmitter configuration.

    :param logger: Custom logger instance to use for logging events
    """

    logger: logging.Logger


class EventEmitter(EventEmitterProtocol[EventTypeT]):
    """
    Event emitter implementation inspired by TypeScript/Node.js EventEmitter.

    Provides both synchronous and asynchronous event emission capabilities.
    Thread-safe for single-threaded use cases.
    """

    def __init__(self, options: Optional[EventEmitterOptions] = None) -> None:
        self._index = -1
        self._subscriptions: Dict[str, List[Subscription]] = {}

        # Use provided logger or create default console logger
        logger = options.get("logger") if options else None
        if logger:
            self._logger = logger.getChild("microsoft.teams.common.events.EventEmitter")
        else:
            self._logger = ConsoleLogger().create_logger("microsoft.teams.common.events.EventEmitter")

    def on(self, event: EventTypeT, handler: EventHandler) -> int:
        """
        Register an event handler.

        Args:
            event: Event name to listen for
            handler: Function to call when event is emitted

        Returns:
            Subscription ID for removing the handler later
        """
        subscription_id = self._get_next_id()

        if event not in self._subscriptions:
            self._subscriptions[event] = []

        self._subscriptions[event].append({"id": subscription_id, "handler": handler})

        self._logger.debug("Registered handler for event '%s' with id %d", event, subscription_id)
        return subscription_id

    def once(self, event: EventTypeT, handler: EventHandler) -> int:
        """
        Register a one-time event handler that will be removed after first execution.

        Args:
            event: Event name to listen for
            handler: Function to call when event is emitted

        Returns:
            Subscription ID for removing the handler later
        """

        def once_wrapper(value: Any) -> None:
            self.off(subscription_id)
            handler(value)

        subscription_id = self._get_next_id()

        if event not in self._subscriptions:
            self._subscriptions[event] = []

        self._subscriptions[event].append({"id": subscription_id, "handler": once_wrapper})

        self._logger.debug("Registered one-time handler for event '%s' with id %d", event, subscription_id)
        return subscription_id

    def off(self, subscription_id: int) -> None:
        """
        Remove an event handler by subscription ID.

        Args:
            subscription_id: ID returned from on() or once()
        """
        for event_name, subscriptions in list(self._subscriptions.items()):
            for i, subscription in enumerate(subscriptions):
                if subscription["id"] == subscription_id:
                    subscriptions.pop(i)
                    self._logger.debug("Removed handler with id %d from event '%s'", subscription_id, event_name)
                    if not subscriptions:
                        del self._subscriptions[event_name]
                    return

    def emit(self, event: EventTypeT, value: Any = None) -> None:
        """
        Emit an event synchronously to all registered handlers.

        Async handlers are run using asyncio.run() in a separate event loop.

        Args:
            event: Event name to emit
            value: Data to pass to event handlers
        """
        if event not in self._subscriptions:
            return

        handler_count = len(self._subscriptions[event])
        self._logger.debug("Emitting event '%s' to %d handler(s)", event, handler_count)

        awaitables: list[Awaitable[None]] = []

        for subscription in self._subscriptions[event][:]:  # Copy to avoid modification during iteration
            try:
                handler = subscription["handler"]

                if asyncio.iscoroutinefunction(handler):
                    awaitables.append(handler(value))
                else:
                    handler(value)
            except Exception as e:
                # Continue executing other handlers even if one fails
                self._logger.error("Handler failed for event '%s': %s", event, e)

        # Handle awaitables if any exist
        if awaitables:
            self._logger.debug("Running %d async handler(s) for event '%s'", len(awaitables), event)

            async def run_async_handlers() -> None:
                results = await asyncio.gather(*awaitables, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self._logger.error("Async handler %d failed for event '%s': %s", i, event, result)

            try:
                # Try to get the current event loop
                loop = asyncio.get_running_loop()
                # If loop is running, schedule the async handlers as tasks
                loop.create_task(run_async_handlers())
                # Note: tasks run in background, emit() doesn't wait for completion
            except RuntimeError:
                # No event loop running, create one
                asyncio.run(run_async_handlers())

    def listener_count(self, event: str) -> int:
        """
        Get the number of listeners for an event.

        Args:
            event: Event name

        Returns:
            Number of registered listeners
        """
        return len(self._subscriptions.get(event, []))

    def event_names(self) -> List[str]:
        """
        Get list of event names that have listeners.

        Returns:
            List of event names
        """
        return list(self._subscriptions.keys())

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """
        Remove all listeners for a specific event or all events.

        Args:
            event: Event name to clear. If None, clears all events.
        """
        if event is None:
            total_handlers = sum(len(handlers) for handlers in self._subscriptions.values())
            self._subscriptions.clear()
            self._logger.debug("Removed all %d handler(s) from all events", total_handlers)
        elif event in self._subscriptions:
            handler_count = len(self._subscriptions[event])
            del self._subscriptions[event]
            self._logger.debug("Removed all %d handler(s) from event '%s'", handler_count, event)

    def _get_next_id(self) -> int:
        """Get next unique subscription ID."""
        self._index += 1
        return self._index
