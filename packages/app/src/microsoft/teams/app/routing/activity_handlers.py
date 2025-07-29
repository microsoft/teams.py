"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Awaitable, Callable, Optional, Pattern, Union, overload

from microsoft.teams.api import (
    ActivityBase,
    MessageActivity,
)

from .activity_context import ActivityContext
from .generated_handlers import GeneratedActivityHandlerMixin
from .router import ActivityRouter
from .type_validation import validate_handler_type


class ActivityHandlerMixin(GeneratedActivityHandlerMixin, ABC):
    """Mixin class providing typed activity handler registration methods."""

    @property
    @abstractmethod
    def router(self) -> ActivityRouter:
        """The activity router instance. Must be implemented by the concrete class."""
        pass

    @property
    @abstractmethod
    def logger(self) -> Logger:
        """The logger instance used by the app."""
        pass

    @overload
    def on_message_pattern(
        self, pattern: str | Pattern[str]
    ) -> Callable[
        [Callable[[ActivityContext[MessageActivity]], Awaitable[None]]],
        Callable[[ActivityContext[MessageActivity]], Awaitable[None]],
    ]:
        """
        Register a message handler that matches a specific text pattern.
        Args:
            pattern: The regex pattern to match against incoming messages

        Usage:

            @app.on_message_pattern(re.compile(r"hello|hi|greetings"))
            async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
                ...

            @app.on_message_pattern("hello")
            async def handle_hello(ctx: ActivityContext[MessageActivity]) -> None:
                ...

        """
        ...

    @overload
    def on_message_pattern(
        self, pattern: str | Pattern[str], handler: Callable[[ActivityContext[MessageActivity]], Awaitable[None]]
    ) -> Callable[[ActivityContext[MessageActivity]], Awaitable[None]]:
        """
        Register a message handler that matches a specific text pattern.
        Args:
            pattern: The regex pattern to match against incoming messages

        Usage:

            async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
                ...
            app.on_message_pattern(re.compile(r"hello|hi|greetings"), handle_greeting)
            app.on_message_pattern("hello", handle_greeting)

        """
        ...

    def on_message_pattern(
        self,
        pattern: Union[str, Pattern[str]],
        handler: Optional[Callable[[ActivityContext[MessageActivity]], Awaitable[None]]] = None,
    ) -> (
        Callable[
            [Callable[[ActivityContext[MessageActivity]], Awaitable[None]]],
            Callable[[ActivityContext[MessageActivity]], Awaitable[None]],
        ]
        | Callable[[ActivityContext[MessageActivity]], Awaitable[None]]
    ):
        """
        Register a message handler that matches a specific text pattern.

        Args:
            pattern: The regex pattern to match against incoming messages
            handler: The async function to call when the pattern matches

        Returns:
            Decorated function or decorator
        """

        def decorator(
            func: Callable[[ActivityContext[MessageActivity]], Awaitable[None]],
        ) -> Callable[[ActivityContext[MessageActivity]], Awaitable[None]]:
            validate_handler_type(self.logger, func, MessageActivity, "on_message", "MessageActivity")

            def selector(ctx: ActivityBase) -> bool:
                if not isinstance(ctx, MessageActivity):
                    return False
                elif isinstance(pattern, str):
                    return ctx.text == pattern
                else:
                    match = pattern.match(ctx.text or "")
                    return match is not None

            self.router.add_handler(selector, func)
            return func

        if handler is not None:
            return decorator(handler)
        return decorator
