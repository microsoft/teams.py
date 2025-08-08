"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from typing import Any, Callable, Dict, Literal, Optional, Type, Union, cast

from .base import EventProtocol
from .types import (
    ActivityEvent,
    ActivityResponseEvent,
    ActivitySentEvent,
    ErrorEvent,
    SignInEvent,
    StartEvent,
    StopEvent,
)

# Core event type literals for type safety
CoreEventType = Literal["activity", "error", "start", "stop", "sign_in", "activity_response", "activity_sent"]
EventType = Union[CoreEventType, str]

# Registry mapping event names to their corresponding event classes
EVENT_TYPE_REGISTRY: Dict[str, Type[EventProtocol]] = {
    "activity": ActivityEvent,
    "error": ErrorEvent,
    "start": StartEvent,
    "stop": StopEvent,
    "sign_in": SignInEvent,
    "activity_response": ActivityResponseEvent,
    "activity_sent": ActivitySentEvent,
}

# Reverse lookup: event class to event name
EVENT_CLASS_REGISTRY: Dict[Type[EventProtocol], str] = {v: k for k, v in EVENT_TYPE_REGISTRY.items()}


def get_event_name_from_type(event_class: Type[Any]) -> EventType:
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
        return cast(EventType, EVENT_CLASS_REGISTRY[event_class])

    raise ValueError(f"Event class {event_class.__name__} is not registered in EVENT_CLASS_REGISTRY")


def is_registered_event(event_name: str) -> bool:
    """
    Check if an event name is registered.

    Args:
        event_name: Event name to check

    Returns:
        True if registered, False otherwise
    """
    return event_name in EVENT_TYPE_REGISTRY


def get_event_type_from_signature(func: Callable[..., Any]) -> Optional[EventType]:
    """
    Extract event type from function signature by inspecting the first parameter's type hint.

    Args:
        func: Function to inspect

    Returns:
        Event type string if detectable, None otherwise
    """
    try:
        sig = inspect.signature(func)
        params = list(sig.parameters.values())

        if not params:
            return None

        # we use the first parameter to do the inference
        first_param = params[0]
        if first_param.annotation == inspect.Parameter.empty:
            return None

        # Get the annotation
        param_type = first_param.annotation

        # Handle string annotations (forward references)
        if isinstance(param_type, str):
            # Try to resolve string annotation to actual type using registry
            if param_type in EVENT_TYPE_REGISTRY:
                return cast(EventType, param_type)

            # Fallback: try class name lookup using registry
            try:
                type_map = {cls.__name__: cls for cls in EVENT_CLASS_REGISTRY.keys()}
                if param_type in type_map:
                    param_type = type_map[param_type]
                else:
                    return None
            except Exception:
                return None

        # Handle actual type objects using registry
        try:
            return get_event_name_from_type(param_type)
        except ValueError:
            return None

    except (ValueError, TypeError):
        return None
