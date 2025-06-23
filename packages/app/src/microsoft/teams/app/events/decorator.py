"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import inspect
from typing import Callable, Optional

from .registry import get_event_name_from_type


def get_event_type_from_signature(func: Callable) -> Optional[str]:
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

        first_param = params[0]
        if first_param.annotation == inspect.Parameter.empty:
            return None

        # Get the annotation
        param_type = first_param.annotation

        # Handle string annotations (forward references)
        if isinstance(param_type, str):
            # Try to resolve string annotation to actual type
            try:
                # Look up by string name in registry
                from .types import ActivityEvent, ErrorEvent, StartEvent, StopEvent, TokenEvent

                type_map = {
                    "ActivityEvent": ActivityEvent,
                    "ErrorEvent": ErrorEvent,
                    "StartEvent": StartEvent,
                    "StopEvent": StopEvent,
                    "TokenEvent": TokenEvent,
                }
                if param_type in type_map:
                    param_type = type_map[param_type]
                else:
                    return None
            except:
                return None

        # Handle actual type objects using registry
        try:
            return get_event_name_from_type(param_type)
        except ValueError:
            return None

    except (ValueError, TypeError):
        return None
