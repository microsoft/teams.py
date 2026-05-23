"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, List, Literal, Optional

from microsoft_teams.api.models import ActivityBase

from .activity_context import ActivityContext
from .activity_route_configs import RouteSelector

# Type alias for activity handlers
ActivityHandler = Callable[[ActivityContext[ActivityBase]], Awaitable[Optional[Any]]]
RouteType = Literal["system", "user"]


@dataclass(frozen=True)
class RouteEntry:
    selector: RouteSelector
    handler: ActivityHandler
    route_name: str | None = None
    route_type: RouteType = "user"


class ActivityRouter:
    """Routes incoming activities to registered handlers using selector functions."""

    def __init__(self):
        self._routes: List[RouteEntry] = []

    def add_handler(
        self,
        selector: RouteSelector,
        handler: ActivityHandler,
        *,
        route_name: str | None = None,
        route_type: RouteType = "user",
    ) -> None:
        """Add a handler for a specific activity configuration."""
        if route_type == "user" and route_name is not None:
            self._routes = [
                route for route in self._routes if not (route.route_name == route_name and route.route_type == "system")
            ]

        self._routes.append(
            RouteEntry(
                selector=selector,
                handler=handler,
                route_name=route_name,
                route_type=route_type,
            )
        )

    def select_handlers(self, activity: ActivityBase) -> List[ActivityHandler]:
        """Select all handlers that match the given activity using selector functions."""
        matching_handlers: List[ActivityHandler] = []
        for route in self._routes:
            if route.selector(activity):
                matching_handlers.append(route.handler)
        return matching_handlers
