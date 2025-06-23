"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Dict, Literal, Type

from .base import EventProtocol
from .types import ActivityEvent, ErrorEvent, StartEvent, StopEvent, TokenEvent

# Core event type literals for type safety
EventType = Literal["activity", "error", "start", "stop", "token"]

# Registry mapping event names to their corresponding event classes
EVENT_TYPE_REGISTRY: Dict[str, Type[EventProtocol]] = {
    "activity": ActivityEvent,
    "error": ErrorEvent,
    "start": StartEvent,
    "stop": StopEvent,
    "token": TokenEvent,
}

# Reverse lookup: event class to event name
EVENT_CLASS_REGISTRY: Dict[Type[EventProtocol], str] = {v: k for k, v in EVENT_TYPE_REGISTRY.items()}


def get_event_name_from_type(event_class: Type) -> str:
    """
    Get event name from event class type.

    Args:
        event_class: Event class type

    Returns:
        Event name string

    Raises:
        ValueError: If event class is not registered
    """
    if event_class in EVENT_CLASS_REGISTRY:
        return EVENT_CLASS_REGISTRY[event_class]

    raise ValueError(f"Event class {event_class.__name__} is not registered in EVENT_CLASS_REGISTRY")


def register_event_type(event_name: str, event_class: Type[EventProtocol]) -> None:
    """
    Register a new event type (for plugin extensibility).

    Args:
        event_name: Name of the event
        event_class: Event class that implements EventProtocol
    """
    EVENT_TYPE_REGISTRY[event_name] = event_class
    EVENT_CLASS_REGISTRY[event_class] = event_name


def is_registered_event(event_name: str) -> bool:
    """
    Check if an event name is registered.

    Args:
        event_name: Event name to check

    Returns:
        True if registered, False otherwise
    """
    return event_name in EVENT_TYPE_REGISTRY
