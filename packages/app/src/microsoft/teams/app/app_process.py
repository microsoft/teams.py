"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Callable, Dict, List, Optional

from microsoft.teams.api import Activity, ActivityBase
from microsoft.teams.common.events import EventEmitter

from .routing.activity_context import ActivityContext
from .routing.generated_handlers import ActivityHandlerMixin
from .routing.router import ActivityHandler, ActivityRouter


class ActivityProcessorMixin(ActivityHandlerMixin, ABC):
    """Mixin that provides activity processing functionality with middleware chain support."""

    @property
    @abstractmethod
    def router(self) -> ActivityRouter:
        """The activity router instance."""

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

        # Create context for middleware chain
        ctx = self._build_context(activity)

        # Get registered handlers for this activity type
        handlers = self.router.select_handlers(activity)

        response = None
        # If no registered handlers, fall back to legacy activity_handler
        if handlers:
            response = await self.execute_middleware_chain(ctx, handlers)

        self.logger.info("Completed processing activity")

        return response

    def _build_context(self, activity: Activity) -> ActivityContext[ActivityBase]:
        """Build the context object for activity processing.

        Args:
            activity: The validated Activity object

        Returns:
            Context object for middleware chain execution
        """

        return ActivityContext(activity)

    async def execute_middleware_chain(
        self, ctx: ActivityContext[ActivityBase], handlers: List[ActivityHandler]
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
                        response = result

            return next_handler

        # Start the chain
        first_handler = await create_next(0)
        await first_handler()

        return response
