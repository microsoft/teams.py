"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC, abstractmethod
from logging import Logger
from typing import Any, Awaitable, Callable, Dict, Optional, Pattern, Union, cast, overload

from microsoft_teams.api import (
    ActivityBase,
    AdaptiveCardInvokeActivity,
    AdaptiveCardInvokeResponse,
    MessageActivity,
    TaskFetchInvokeActivity,
    TaskModuleInvokeResponse,
    TaskSubmitInvokeActivity,
)

from .activity_context import ActivityContext
from .generated_handlers import GeneratedActivityHandlerMixin
from .router import ActivityRouter
from .type_helpers import InvokeHandler, InvokeHandlerUnion
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

    @overload
    def on_dialog_open(
        self,
    ) -> Callable[
        [InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse]],
        InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse],
    ]:
        """
        Register a global dialog open handler for all dialog open events.

        Usage:

            @app.on_dialog_open
            async def handle_all_dialogs(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)

        """
        ...

    @overload
    def on_dialog_open(
        self,
        dialog_id_or_handler: InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse],
    ) -> InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse]:
        """
        Register a global dialog open handler for all dialog open events.

        Usage:

            async def handle_all_dialogs(ctx: ActivityContext[TaskFetchInvokeActivity]) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)
            app.on_dialog_open(handle_all_dialogs)

        """
        ...

    @overload
    def on_dialog_open(
        self, dialog_id_or_handler: str
    ) -> Callable[
        [InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse]],
        InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse],
    ]:
        """
        Register a dialog open handler that matches a specific dialog_id.

        Args:
            dialog_id_or_handler: The dialog identifier to match against the 'dialog_id' field in activity data

        Usage:

            @app.on_dialog_open("simple_form")
            async def handle_simple_form_open(
                ctx: ActivityContext[TaskFetchInvokeActivity]
            ) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)

        """
        ...

    @overload
    def on_dialog_open(
        self,
        dialog_id_or_handler: str,
        handler: InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse],
    ) -> InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse]:
        """
        Register a dialog open handler that matches a specific dialog_id.

        Args:
            dialog_id_or_handler: The dialog identifier to match against the 'dialog_id' field in activity data
            handler: The async function to call when the dialog_id matches

        Usage:

            async def handle_simple_form_open(
                ctx: ActivityContext[TaskFetchInvokeActivity]
            ) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)
            app.on_dialog_open("simple_form", handle_simple_form_open)

        """
        ...

    def on_dialog_open(
        self,
        dialog_id_or_handler: Union[str, InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse], None] = None,
        handler: Optional[InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse]] = None,
    ) -> InvokeHandlerUnion[TaskFetchInvokeActivity, TaskModuleInvokeResponse]:
        """
        Register a dialog open handler.

        Args:
            dialog_id_or_handler: Optional dialog identifier to match against the 'dialog_id' field in activity data,
                                 or a handler function to match all dialog open events.
            handler: The async function to call when the event matches

        Returns:
            Decorated function or decorator
        """

        # Handle case where first argument is actually a handler function (no dialog_id)
        if callable(dialog_id_or_handler):
            handler = dialog_id_or_handler
            dialog_id_or_handler = None

        def decorator(
            func: InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse],
        ) -> InvokeHandler[TaskFetchInvokeActivity, TaskModuleInvokeResponse]:
            validate_handler_type(
                self.logger, func, TaskFetchInvokeActivity, "on_dialog_open", "TaskFetchInvokeActivity"
            )

            def selector(ctx: ActivityBase) -> bool:
                if not isinstance(ctx, TaskFetchInvokeActivity):
                    return False
                # If no dialog_id specified, match all dialog open events
                if dialog_id_or_handler is None:
                    return True
                # Otherwise, match specific dialog_id
                data = ctx.value.data if ctx.value else None
                if not isinstance(data, dict):
                    return False
                data = cast(Dict[str, Any], data)
                dialog_id = data.get("dialog_id")
                if dialog_id is not None and not isinstance(dialog_id, str):
                    self.logger.warning(
                        f"Expected 'dialog_id' to be a string, got {type(dialog_id).__name__}: {dialog_id}"
                    )
                    return False
                return dialog_id == dialog_id_or_handler

            self.router.add_handler(selector, func)
            return func

        if handler is not None:
            return decorator(handler)
        return decorator

    @overload
    def on_dialog_submit(
        self,
    ) -> Callable[
        [InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]],
        InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse],
    ]:
        """
        Register a global dialog submit handler for all dialog submit events.

        Usage:

            @app.on_dialog_submit
            async def handle_all_submits(ctx: ActivityContext[TaskSubmitInvokeActivity]) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)

        """
        ...

    @overload
    def on_dialog_submit(
        self,
        action_or_handler: InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse],
    ) -> InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]:
        """
        Register a global dialog submit handler for all dialog submit events.

        Usage:

            async def handle_all_submits(ctx: ActivityContext[TaskSubmitInvokeActivity]) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)
            app.on_dialog_submit(handle_all_submits)

        """
        ...

    @overload
    def on_dialog_submit(
        self, action_or_handler: str
    ) -> Callable[
        [InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]],
        InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse],
    ]:
        """
        Register a dialog submit handler that matches a specific action.

        Args:
            action_or_handler: The action identifier to match against the 'action' field in activity data

        Usage:

            @app.on_dialog_submit("submit_user_form")
            async def handle_user_form_submit(
                ctx: ActivityContext[TaskSubmitInvokeActivity]
            ) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)

        """
        ...

    @overload
    def on_dialog_submit(
        self,
        action_or_handler: str,
        handler: InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse],
    ) -> InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]:
        """
        Register a dialog submit handler that matches a specific action.

        Args:
            action_or_handler: The action identifier to match against the 'action' field in activity data
            handler: The async function to call when the action matches

        Usage:

            async def handle_user_form_submit(
                ctx: ActivityContext[TaskSubmitInvokeActivity]
            ) -> TaskModuleInvokeResponse:
                return InvokeResponse(...)
            app.on_dialog_submit("submit_user_form", handle_user_form_submit)

        """
        ...

    def on_dialog_submit(
        self,
        action_or_handler: Union[str, InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse], None] = None,
        handler: Optional[InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]] = None,
    ) -> InvokeHandlerUnion[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]:
        """
        Register a dialog submit handler.

        Args:
            action_or_handler: Optional action identifier to match against the 'action' field in activity data,
                              or a handler function to match all dialog submit events.
            handler: The async function to call when the event matches

        Returns:
            Decorated function or decorator
        """

        # Handle case where first argument is actually a handler function (no action)
        if callable(action_or_handler):
            handler = action_or_handler
            action_or_handler = None

        def decorator(
            func: InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse],
        ) -> InvokeHandler[TaskSubmitInvokeActivity, TaskModuleInvokeResponse]:
            validate_handler_type(
                self.logger, func, TaskSubmitInvokeActivity, "on_dialog_submit", "TaskSubmitInvokeActivity"
            )

            def selector(ctx: ActivityBase) -> bool:
                if not isinstance(ctx, TaskSubmitInvokeActivity):
                    return False
                # If no action specified, match all dialog submit events
                if action_or_handler is None:
                    return True
                # Otherwise, match specific action
                data = ctx.value.data if ctx.value else None
                if not isinstance(data, dict):
                    return False
                data = cast(Dict[str, Any], data)
                action = data.get("action")
                if action is not None and not isinstance(action, str):
                    self.logger.warning(f"Expected 'action' to be a string, got {type(action).__name__}: {action}")
                    return False
                return action == action_or_handler

            self.router.add_handler(selector, func)
            return func

        if handler is not None:
            return decorator(handler)
        return decorator

    @overload
    def on_card_action(
        self,
    ) -> Callable[
        [InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]],
        InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse],
    ]:
        """
        Register a global card action handler for all card action events.

        Usage:

            @app.on_card_action
            async def handle_all_actions(
                ctx: ActivityContext[AdaptiveCardInvokeActivity],
            ) -> AdaptiveCardInvokeResponse:
                return InvokeResponse(...)

        """
        ...

    @overload
    def on_card_action(
        self,
        action_or_handler: InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse],
    ) -> InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]:
        """
        Register a global card action handler for all card action events.

        Usage:

            async def handle_all_actions(
                ctx: ActivityContext[AdaptiveCardInvokeActivity],
            ) -> AdaptiveCardInvokeResponse:
                return InvokeResponse(...)
            app.on_card_action(handle_all_actions)

        """
        ...

    @overload
    def on_card_action(
        self, action_or_handler: str
    ) -> Callable[
        [InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]],
        InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse],
    ]:
        """
        Register a card action handler that matches a specific action.

        Args:
            action_or_handler: The action identifier to match against the 'action' field in activity data

        Usage:

            @app.on_card_action("submit_basic")
            async def handle_basic_submit(
                ctx: ActivityContext[AdaptiveCardInvokeActivity]
            ) -> AdaptiveCardInvokeResponse:
                return InvokeResponse(...)

        """
        ...

    @overload
    def on_card_action(
        self,
        action_or_handler: str,
        handler: InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse],
    ) -> InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]:
        """
        Register a card action handler that matches a specific action.

        Args:
            action_or_handler: The action identifier to match against the 'action' field in activity data
            handler: The async function to call when the action matches

        Usage:

            async def handle_basic_submit(
                ctx: ActivityContext[AdaptiveCardInvokeActivity]
            ) -> AdaptiveCardInvokeResponse:
                return InvokeResponse(...)
            app.on_card_action("submit_basic", handle_basic_submit)

        """
        ...

    def on_card_action(
        self,
        action_or_handler: Union[
            str, InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse], None
        ] = None,
        handler: Optional[InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]] = None,
    ) -> InvokeHandlerUnion[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]:
        """
        Register a card action handler.

        Args:
            action_or_handler: Optional action identifier to match against the 'action' field in activity data,
                              or a handler function to match all card action events.
            handler: The async function to call when the event matches

        Returns:
            Decorated function or decorator
        """

        # Handle case where first argument is actually a handler function (no action)
        if callable(action_or_handler):
            handler = action_or_handler
            action_or_handler = None

        def decorator(
            func: InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse],
        ) -> InvokeHandler[AdaptiveCardInvokeActivity, AdaptiveCardInvokeResponse]:
            validate_handler_type(
                self.logger, func, AdaptiveCardInvokeActivity, "on_card_action", "AdaptiveCardInvokeActivity"
            )

            def selector(ctx: ActivityBase) -> bool:
                if not isinstance(ctx, AdaptiveCardInvokeActivity):
                    return False
                # If no action specified, match all card action events
                if action_or_handler is None:
                    return True
                # Otherwise, match specific action
                if not ctx.value or not ctx.value.action:
                    return False
                data = ctx.value.action.data
                action = data.get("action")
                if action is not None and not isinstance(action, str):
                    self.logger.warning(f"Expected 'action' to be a string, got {type(action).__name__}: {action}")
                    return False
                return action == action_or_handler

            self.router.add_handler(selector, func)
            return func

        if handler is not None:
            return decorator(handler)
        return decorator
