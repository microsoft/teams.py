"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    from .context import Context

# Type alias for activity handlers
ActivityHandler = Callable[["Context"], Union[Awaitable[Optional[Dict[str, Any]]], Optional[Dict[str, Any]]]]


class ActivityRouter:
    """Routes incoming activities to registered handlers based on activity type."""

    def __init__(self):
        self._handlers: Dict[str, List[ActivityHandler]] = {}

    def add_handler(self, activity_type: str, handler: ActivityHandler) -> None:
        """Add a handler for a specific activity type."""
        if activity_type not in self._handlers:
            self._handlers[activity_type] = []
        self._handlers[activity_type].append(handler)

    def get_handlers(self, activity_type: str) -> List[ActivityHandler]:
        """Get all handlers for a specific activity type."""
        return self._handlers.get(activity_type, [])
