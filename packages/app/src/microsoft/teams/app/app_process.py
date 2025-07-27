"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import Any, Callable, Dict, List, Optional

from microsoft.teams.api import ActivityBase

from .routing.activity_context import ActivityContext
from .routing.router import ActivityHandler, ActivityRouter


class ActivityProcessor:
    """Provides activity processing functionality with middleware chain support."""

    def __init__(self, router: ActivityRouter, logger: Logger) -> None:
        self.router = router
        self.logger = logger

    async def process_activity(self, activityCtx: ActivityContext[ActivityBase]) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Received activity: {activityCtx.activity}")

        # Get registered handlers for this activity type
        handlers = self.router.select_handlers(activityCtx.activity)

        response = None
        # If no registered handlers, fall back to legacy activity_handler
        if handlers:
            response = await self.execute_middleware_chain(activityCtx, handlers)

        self.logger.info("Completed processing activity")

        return response

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
