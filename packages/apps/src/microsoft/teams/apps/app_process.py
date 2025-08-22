"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from logging import Logger
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast

from microsoft.teams.api import (
    ActivityBase,
    ActivityParams,
    ApiClient,
    ConversationReference,
    GetUserTokenParams,
    InvokeResponse,
    JsonWebToken,
    SentActivity,
    TokenProtocol,
    is_invoke_response,
)
from microsoft.teams.cards import AdaptiveCard
from microsoft.teams.common import Client, ClientOptions, LocalStorage, Storage

if TYPE_CHECKING:
    from .app_events import EventManager
from .app_tokens import AppTokens
from .events import ActivityEvent, ActivityResponseEvent, ActivitySentEvent
from .plugins import PluginActivityEvent, PluginBase, Sender
from .routing.activity_context import ActivityContext
from .routing.router import ActivityHandler, ActivityRouter


class ActivityProcessor:
    """Provides activity processing functionality with middleware chain support."""

    def __init__(
        self,
        router: ActivityRouter,
        logger: Logger,
        id: Optional[str],
        storage: Union[Storage[str, Any], LocalStorage[Any]],
        default_connection_name: str,
        http_client: Client,
        token: AppTokens,
    ) -> None:
        self.router = router
        self.logger = logger
        self.id = id
        self.storage = storage
        self.default_connection_name = default_connection_name
        self.http_client = http_client
        self.tokens = token

        # This will be set after the EventManager is initialized due to
        # a circular dependency
        self.event_manager: Optional["EventManager"] = None

    async def _build_context(
        self, activity: ActivityBase, token: TokenProtocol, plugins: List[PluginBase], sender: Sender
    ) -> ActivityContext[ActivityBase]:
        """Build the context object for activity processing.

        Args:
            activity: The validated Activity object

        Returns:
            Context object for middleware chain execution
        """

        service_url = activity.service_url or token.service_url
        conversation_ref = ConversationReference(
            service_url=service_url,
            activity_id=activity.id,
            bot=activity.recipient,
            channel_id=activity.channel_id,
            conversation=activity.conversation,
            locale=activity.locale,
            user=activity.from_,
        )
        api_client = ApiClient(service_url, self.http_client.clone(ClientOptions(token=self.tokens.bot)))

        # Check if user is signed in
        is_signed_in = False
        user_token: Optional[TokenProtocol] = None
        try:
            user_token_res = await api_client.users.token.get(
                GetUserTokenParams(
                    connection_name=self.default_connection_name or "default",
                    user_id=activity.from_.id,
                    channel_id=activity.channel_id,
                )
            )
            user_token = JsonWebToken(user_token_res.token)
            is_signed_in = True
        except Exception:
            # User token not available
            pass

        activityCtx = ActivityContext(
            activity,
            self.id or "",
            self.logger,
            self.storage,
            api_client,
            user_token,
            conversation_ref,
            is_signed_in,
            self.default_connection_name,
            sender,
        )

        send = activityCtx.send

        async def updated_send(
            message: str | ActivityParams | AdaptiveCard, conversation_ref: Optional[ConversationReference] = None
        ) -> SentActivity:
            res = await send(message, conversation_ref)

            if not self.event_manager:
                raise ValueError("EventManager was not initialized properly")

            self.logger.debug("Calling on_activity_sent for plugins")

            ref = conversation_ref or activityCtx.conversation_ref

            await self.event_manager.on_activity_sent(
                sender, ActivitySentEvent(sender=sender, activity=res, conversation_ref=ref), plugins=plugins
            )
            return res

        activityCtx.send = updated_send

        return activityCtx

    async def process_activity(
        self, plugins: List[PluginBase], sender: Sender, event: ActivityEvent
    ) -> Optional[InvokeResponse[Any]]:
        activityCtx = await self._build_context(event.activity, event.token, plugins, sender)

        self.logger.debug(f"Received activity: {activityCtx.activity}")

        # Get registered handlers for this activity type
        handlers = self.router.select_handlers(activityCtx.activity)

        def create_route(plugin: PluginBase) -> ActivityHandler:
            async def route(ctx: ActivityContext[ActivityBase]) -> Optional[Any]:
                await plugin.on_activity(
                    PluginActivityEvent(
                        sender=sender,
                        activity=event.activity,
                        token=event.token,
                        conversation_ref=activityCtx.conversation_ref,
                    )
                )
                await ctx.next()

            return route

        plugin_routes = [
            create_route(plugin)
            for plugin in plugins
            if hasattr(plugin, "on_activity_event") and callable(plugin.on_activity)
        ]
        handlers = plugin_routes + handlers

        response: Optional[InvokeResponse[Any]] = None

        # If no registered handlers, fall back to legacy activity_handler
        if handlers:
            middleware_result = await self.execute_middleware_chain(activityCtx, handlers)
            if not self.event_manager:
                raise ValueError("EventManager was not initialized properly")

            if not middleware_result or not is_invoke_response(middleware_result):
                response = InvokeResponse[Any](status=200, body=middleware_result)
            else:
                response = cast(InvokeResponse[Any], middleware_result)

            await self.event_manager.on_activity_response(
                sender,
                ActivityResponseEvent(
                    activity=event.activity, response=response, conversation_ref=activityCtx.conversation_ref
                ),
                plugins=plugins,
            )

        self.logger.debug("Completed processing activity")

        return response

    async def execute_middleware_chain(
        self, ctx: ActivityContext[ActivityBase], handlers: List[ActivityHandler]
    ) -> Optional[Dict[str, Any]]:
        """Execute the middleware chain for activity handlers.

        Args:
            ctx: Context object for the activity
            handlers: List of activity handlers to execute

        Returns:
            Final response from handlers, if any
        """
        if len(handlers) == 0:
            return None

        # Track the final response
        response = None

        # Create the middleware chain
        async def create_next(index: int) -> Callable[[], Any]:
            async def next_handler():
                nonlocal response
                if index < len(handlers):
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

                    # Update the response iff response hasn't already been received
                    if result is not None:
                        response = result

            return next_handler

        # Start the chain
        first_handler = await create_next(0)
        await first_handler()

        return response
