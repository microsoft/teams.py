"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
from time import perf_counter
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union, cast

from microsoft_teams.api import (
    ActivityBase,
    ActivityParams,
    ActivityTypeAdapter,
    ApiClient,
    ApiClientSettings,
    ConversationReference,
    InvokeResponse,
    SentActivity,
    TokenProtocol,
    is_invoke_response,
)
from microsoft_teams.api.activities import Activity as ValidatedActivity
from microsoft_teams.api.activities.invoke_activity import InvokeActivity as InvokeActivityBase
from microsoft_teams.api.auth.cloud_environment import PUBLIC, CloudEnvironment
from microsoft_teams.api.clients.user.params import GetUserTokenParams
from microsoft_teams.cards import AdaptiveCard
from microsoft_teams.common import Client, LocalStorage, Storage
from opentelemetry.trace import Span

if TYPE_CHECKING:
    from .app_events import EventManager

from .auth_provider import AppAuthProvider
from .diagnostics._constants import APP_ATTRIBUTE_NAMES, APP_HANDLER_DISPATCHES, APP_SPAN_NAMES
from .diagnostics._helpers import (
    get_tracer,
    record_activity_received,
    record_exception,
    record_handler_dispatched,
    record_handler_duration,
    record_handler_failure,
    record_handler_unmatched,
    record_turn_duration,
)
from .events import ActivityEvent, ActivityResponseEvent, ActivitySentEvent, ErrorEvent
from .plugins import PluginActivityEvent, PluginBase, StreamCancelledError
from .routing.activity_context import ActivityContext
from .routing.router import ActivityHandler, ActivityRouter
from .token_manager import TokenManager
from .utils import extract_tenant_id

logger = logging.getLogger(__name__)


class ActivityProcessor:
    """Provides activity processing functionality with middleware chain support."""

    def __init__(
        self,
        router: ActivityRouter,
        id: Optional[str],
        storage: Union[Storage[str, Any], LocalStorage[Any]],
        default_connection_name: str,
        http_client: Client,
        token_manager: TokenManager,
        auth_provider: AppAuthProvider,
        api_client_settings: Optional[ApiClientSettings],
        cloud: CloudEnvironment = PUBLIC,
    ) -> None:
        self.router = router
        self.id = id
        self.storage = storage
        self.default_connection_name = default_connection_name
        self.http_client = http_client
        self.token_manager = token_manager
        self.auth_provider = auth_provider
        self.api_client_settings = api_client_settings
        self.cloud = cloud

        # This will be set after the EventManager is initialized due to
        # a circular dependency
        self.event_manager: Optional["EventManager"] = None

    async def _build_context(
        self,
        activity: ActivityBase,
        token: TokenProtocol,
        plugins: List[PluginBase],
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
        api_client = ApiClient(
            service_url,
            self.http_client,
            self.api_client_settings,
            auth_provider=self.auth_provider,
            agent_user=activity.recipient.agent_user,
        )

        # Check if user is signed in
        is_signed_in = False
        user_token: Optional[str] = None
        try:
            user_token_res = await api_client.users.get_token(
                GetUserTokenParams(
                    channel_id=activity.channel_id,
                    user_id=activity.from_.id,
                    connection_name=self.default_connection_name,
                )
            )

            user_token = user_token_res.token
            is_signed_in = True
        except Exception:
            # User token not available
            logger.debug("No user token available")
            pass

        tenant_id = extract_tenant_id(activity)

        activityCtx = ActivityContext(
            activity,
            self.id or "",
            self.storage,
            api_client,
            user_token,
            conversation_ref,
            is_signed_in,
            self.default_connection_name,
            app_token=lambda: self.token_manager.get_graph_token(tenant_id),
            cloud=self.cloud,
        )

        send = activityCtx.send

        async def updated_send(
            message: str | ActivityParams | AdaptiveCard,
            conversation_ref: Optional[ConversationReference] = None,
        ) -> SentActivity:
            res = await send(message, conversation_ref)

            if not self.event_manager:
                raise ValueError("EventManager was not initialized properly")

            logger.debug("Calling on_activity_sent for plugins")
            ref = conversation_ref or activityCtx.conversation_ref

            await self.event_manager.on_activity_sent(
                ActivitySentEvent(activity=res, conversation_ref=ref),
                plugins=plugins,
            )
            return res

        activityCtx.send = updated_send

        async def handle_chunk(chunk_activity: SentActivity):
            if self.event_manager:
                await self.event_manager.on_activity_sent(
                    ActivitySentEvent(activity=chunk_activity, conversation_ref=conversation_ref),
                    plugins=plugins,
                )

        async def handle_close(close_activity: SentActivity):
            if self.event_manager:
                await self.event_manager.on_activity_sent(
                    ActivitySentEvent(activity=close_activity, conversation_ref=conversation_ref),
                    plugins=plugins,
                )

        activityCtx.stream.on_chunk(handle_chunk)
        activityCtx.stream.on_close(handle_close)

        return activityCtx

    async def process_activity(self, plugins: List[PluginBase], event: ActivityEvent) -> InvokeResponse[Any]:
        activity_dict = event.body.model_dump(by_alias=True, exclude_none=True)
        activity = ActivityTypeAdapter.validate_python(activity_dict)
        activity_type = activity.type
        record_activity_received(activity_type)

        with get_tracer().start_as_current_span(
            APP_SPAN_NAMES.turn,
            record_exception=False,
            set_status_on_exception=False,
        ) as turn_span:
            self._set_turn_span_attributes(turn_span, activity)
            turn_started_at = perf_counter()
            try:
                response = await self._process_activity_core(plugins, event, activity)
            except Exception as error:
                record_exception(turn_span, error)
                raise
            finally:
                record_turn_duration((perf_counter() - turn_started_at) * 1000, activity_type)

        return response

    async def _process_activity_core(
        self, plugins: List[PluginBase], event: ActivityEvent, activity: ValidatedActivity
    ) -> InvokeResponse[Any]:
        activityCtx = await self._build_context(activity, event.token, plugins)

        logger.debug(f"Received activity: {activityCtx.activity}")

        # Get registered handlers for this activity type
        handlers = self.router.select_handlers(activityCtx.activity)

        def create_route(plugin: PluginBase) -> ActivityHandler:
            async def route(ctx: ActivityContext[ActivityBase]) -> Optional[Any]:
                await plugin.on_activity(
                    PluginActivityEvent(
                        activity=activity,
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

        response: InvokeResponse[Any]

        if not handlers:
            record_handler_unmatched(activity.type, self._invoke_name(activity))

        if not self.event_manager:
            raise ValueError("EventManager was not initialized properly")

        try:
            # If no registered handlers, middleware_result is set to None
            middleware_result = await self.execute_middleware_chain(activityCtx, handlers)

            await activityCtx.stream.close()

            if is_invoke_response(middleware_result):
                response = cast(InvokeResponse[Any], middleware_result)
            else:
                response = InvokeResponse[Any](status=200, body=middleware_result)

            await self.event_manager.on_activity_response(
                ActivityResponseEvent(
                    activity=activity,
                    response=response,
                    conversation_ref=activityCtx.conversation_ref,
                ),
                plugins=plugins,
            )
        except StreamCancelledError:
            logger.debug("Activity processing was cancelled (stream stopped)")
            await activityCtx.stream.close()
            response = InvokeResponse[Any](status=200)
        except Exception as error:
            await self.event_manager.on_error(ErrorEvent(error=error, activity=activity), plugins)
            raise error

        logger.debug("Completed processing activity")

        return response

    def _activity_attributes(self, activity: ActivityBase) -> dict[str, str]:
        attributes = {
            APP_ATTRIBUTE_NAMES.activity_type: activity.type,
            APP_ATTRIBUTE_NAMES.activity_id: activity.id,
            APP_ATTRIBUTE_NAMES.conversation_id: activity.conversation.id,
            APP_ATTRIBUTE_NAMES.channel_id: activity.channel_id,
            APP_ATTRIBUTE_NAMES.bot_id: activity.recipient.id,
        }
        if activity.service_url:
            attributes[APP_ATTRIBUTE_NAMES.service_url] = activity.service_url
        return attributes

    def _handler_dispatch(self, activity: ActivityBase) -> str:
        if isinstance(activity, InvokeActivityBase):
            return APP_HANDLER_DISPATCHES.invoke
        return APP_HANDLER_DISPATCHES.type

    def _handler_type(self, activity: ActivityBase) -> str:
        if isinstance(activity, InvokeActivityBase):
            return activity.name
        return activity.type

    def _invoke_name(self, activity: ActivityBase) -> str | None:
        if isinstance(activity, InvokeActivityBase):
            return activity.name
        return None

    def _set_turn_span_attributes(self, span: Span, activity: ActivityBase) -> None:
        for key, value in self._activity_attributes(activity).items():
            span.set_attribute(key, value)

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
                    result = await self._execute_handler(ctx, handlers[index])

                    # Update the response iff response hasn't already been received
                    if result is not None:
                        response = result

            return next_handler

        # Start the chain
        first_handler = await create_next(0)
        await first_handler()

        return response

    async def _execute_handler(self, ctx: ActivityContext[ActivityBase], handler: ActivityHandler) -> Optional[Any]:
        handler_type = self._handler_type(ctx.activity)
        handler_dispatch = self._handler_dispatch(ctx.activity)
        attributes = {
            APP_ATTRIBUTE_NAMES.handler_type: handler_type,
            APP_ATTRIBUTE_NAMES.handler_dispatch: handler_dispatch,
        }
        record_handler_dispatched(handler_type, handler_dispatch)
        started_at = perf_counter()
        with get_tracer().start_as_current_span(
            APP_SPAN_NAMES.handler,
            record_exception=False,
            set_status_on_exception=False,
        ) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
            try:
                return await handler(ctx)
            except Exception as exception:
                record_exception(span, exception)
                record_handler_failure(handler_type, handler_dispatch)
                raise
            finally:
                record_handler_duration((perf_counter() - started_at) * 1000, handler_type, handler_dispatch)
