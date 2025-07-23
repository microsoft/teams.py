"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from microsoft.teams.api import Activity
from microsoft.teams.common.events import EventEmitter

from .events import ErrorEvent
from .routing.activity_context import ActivityContext
from .routing.generated_handlers import ActivityHandlerMixin
from .routing.router import ActivityRouter

# Type alias for activity handlers
ActivityHandler = Callable[[ActivityContext], Awaitable[Optional[Dict[str, Any]]]]
T = TypeVar("T", bound=Activity)


class ActivityProcessorMixin(ActivityHandlerMixin, ABC):
    """Mixin that provides activity processing functionality with middleware chain support."""

    _router_instance = ActivityRouter()

    @property
    def router(self) -> ActivityRouter:
        """The activity router instance."""
        return self._router_instance

    @property
    @abstractmethod
    def logger(self) -> Logger:
        """The logger instance used by the app."""

    @property
    @abstractmethod
    def events(self) -> EventEmitter:
        """The event emitter instance used by the app."""

    async def process_activity(self, activity: Activity) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Received activity: {activity}")

        try:
            # Create context for middleware chain
            ctx = self._build_context(activity)

            # Get registered handlers for this activity type
            handlers = self.router.select_handlers(activity)

            response = None
            # If no registered handlers, fall back to legacy activity_handler
            if handlers:
                response = await self.execute_middleware_chain(ctx, handlers)

            self.logger.info(f"Completed processing activity {activity.id}")

            return response
        except Exception as error:
            self.logger.error(f"Failed to process activity {activity.id}: {error}")

            self._events.emit(
                "error",
                ErrorEvent(
                    error,
                    context={"method": "process_activity", "activity_id": activity.id, "activity_type": activity.type},
                ),
            )
            raise

    def _build_context(self, activity: T) -> ActivityContext[T]:
        """Build the context object for activity processing.

        Args:
            activity: The validated Activity object

        Returns:
            Context object for middleware chain execution
        """

        return ActivityContext(activity)

    async def execute_middleware_chain(
        self, ctx: ActivityContext, handlers: List[ActivityHandler]
    ) -> Optional[Dict[str, Any]]:
        """Execute the middleware chain for activity handlers.

        Args:
            ctx: Context object for the activity
            handlers: List of activity handlers to execute

        Returns:
            Response from handlers, if any
        """
        if not handlers:
            return None

        # Track response from handlers
        response = None

        # Create the middleware chain
        async def create_next(index: int) -> Callable[[], Any]:
            async def next_handler():
                nonlocal response
                if index < len(handlers) and response is None:
                    # Set up next handler for current context
                    if index + 1 < len(handlers):
                        ctx.set_next(await create_next(index + 1))
                    else:
                        # No-op async function for last handler
                        async def noop():
                            pass

                        ctx.set_next(noop)

                    # Execute current handler and capture return value
                    result = await handlers[index](ctx)

                    # If handler returned a response, stop the chain
                    if result is not None:
                        response = result if isinstance(result, dict) else None

            return next_handler

        # Start the chain
        first_handler = await create_next(0)
        await first_handler()

        return response
