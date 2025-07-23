"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from microsoft.teams.api.models import ActivityBase

from .activity_context import ActivityContext
from .activity_route_configs import RouteSelector

# Type alias for activity handlers
ActivityHandler = Callable[[ActivityContext], Union[Awaitable[Optional[Any]], Optional[Dict[str, Any]]]]


class ActivityRouter:
    """Routes incoming activities to registered handlers using selector functions."""

    def __init__(self):
        self._routes: List[tuple[RouteSelector, ActivityHandler]] = []

    def add_handler(self, selector: RouteSelector, handler: ActivityHandler) -> None:
        """Add a handler for a specific activity configuration."""
        self._routes.append((selector, handler))

    def select_handlers(self, activity: ActivityBase) -> List[ActivityHandler]:
        """Select all handlers that match the given activity using selector functions."""
        matching_handlers = []
        for selector, handler in self._routes:
            if selector(activity):
                matching_handlers.append(handler)
        return matching_handlers
