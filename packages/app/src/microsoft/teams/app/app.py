"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import importlib.metadata
import os
from dataclasses import dataclass
from logging import Logger
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast, overload

from dotenv import find_dotenv, load_dotenv
from microsoft.teams.api import (
    ActivityBase,
    ActivityTypeAdapter,
    ApiClient,
    ClientCredentials,
    ConversationReference,
    Credentials,
    GetUserTokenParams,
    JsonWebToken,
    TokenProtocol,
)
from microsoft.teams.common import Client, ClientOptions, ConsoleLogger, EventEmitter, LocalStorage

from .app_oauth import OauthHandlers
from .app_process import ActivityProcessor
from .events import (
    ActivityEvent,
    ErrorEvent,
    EventType,
    StartEvent,
    StopEvent,
    get_event_type_from_signature,
    is_registered_event,
)
from .http_plugin import HttpActivityEvent, HttpPlugin
from .options import AppOptions
from .plugins import Plugin, PluginActivityResponseEvent, PluginStartEvent
from .routing import ActivityContext, ActivityHandlerMixin, ActivityRouter

version = importlib.metadata.version("microsoft-teams-app")

F = TypeVar("F", bound=Callable[..., Any])
load_dotenv(find_dotenv(usecwd=True))

USER_AGENT = f"teams.py[app]/{version}"


@dataclass
class AppTokens:
    """Application tokens for API access."""

    bot: Optional[TokenProtocol] = None
    graph: Optional[TokenProtocol] = None


class App(ActivityHandlerMixin):
    """
    The main Teams application orchestrator.

    Manages plugins, tokens, and application lifecycle for Microsoft Teams apps.
    """

    def __init__(self, options: Optional[AppOptions] = None):
        self.options = options or AppOptions()

        self.log = self.options.logger or ConsoleLogger().create_logger("@teams/app")
        self.storage = self.options.storage or LocalStorage()

        self.http_client = Client(
            ClientOptions(
                headers={"User-Agent": USER_AGENT},
            )
        )

        self._events = EventEmitter[EventType]()
        self._router = ActivityRouter()
        self._activity_processor = ActivityProcessor(self._router, self.log)

        self._tokens = AppTokens()
        self.credentials = self._init_credentials()

        self.api = ApiClient(
            "https://smba.trafficmanager.net/teams",
            self.http_client.clone(ClientOptions(token=lambda: self.tokens.bot)),
        )

        plugins: List[Plugin] = list(self.options.plugins or [])

        http_plugin = None
        for i, plugin in enumerate(plugins):
            if isinstance(plugin, HttpPlugin):
                http_plugin = plugin
                plugins.pop(i)
                break

        if not http_plugin:
            app_id = None
            if self.credentials and hasattr(self.credentials, "client_id"):
                app_id = self.credentials.client_id

            http_plugin = HttpPlugin(app_id, self.log, self.options.enable_token_validation, self.handle_activity)

        plugins.append(http_plugin)

        self.plugins = plugins
        self.http = http_plugin

        # TODO: When plugin architecture is done, remove this manual wiring
        self.http.activity_handler = self.handle_activity

        self._port: Optional[int] = None
        self._running = False

        # default event handlers
        oauth_handlers = OauthHandlers(
            default_connection_name=self.options.default_connection_name,
            event_emitter=self._events,
        )
        self.on_signin_token_exchange(oauth_handlers.sign_in_token_exchange)
        self.on_signin_verify_state(oauth_handlers.sign_in_verify_state)

    @property
    def port(self) -> Optional[int]:
        """Port the app is running on."""
        return self._port

    @property
    def is_running(self) -> bool:
        """Whether the app is currently running."""
        return self._running

    @property
    def tokens(self) -> AppTokens:
        """Current authentication tokens."""
        return self._tokens

    @property
    def logger(self) -> Logger:
        """The logger instance used by the app."""
        return self.log

    @property
    def events(self) -> EventEmitter[EventType]:
        """The event emitter instance used by the app."""
        return self._events

    @property
    def router(self) -> ActivityRouter:
        """The activity router instance."""
        return self._router

    @property
    def id(self) -> Optional[str]:
        """The app's ID from tokens."""
        return getattr(self._tokens.bot, "app_id", None) or getattr(self._tokens.graph, "app_id", None)

    @property
    def name(self) -> Optional[str]:
        """The app's name from tokens."""
        return getattr(self._tokens.bot, "app_display_name", None) or getattr(
            self._tokens.graph, "app_display_name", None
        )

    async def start(self, port: Optional[int] = None) -> None:
        """
        Start the Teams application and begin serving HTTP requests.

        This method will block and keep the application running until stopped.
        This is the main entry point for running your Teams app.

        Args:
            port: Port to listen on (defaults to PORT env var or 3978)
        """
        if self._running:
            self.log.warning("App is already running")
            return

        self._port = port or int(os.getenv("PORT", "3978"))

        try:
            await self._refresh_tokens(force=True)
            self._running = True

            # Start all plugins except HTTP plugin first
            for plugin in self.plugins:
                if plugin is not self.http:
                    event = PluginStartEvent(port=self._port)
                    await plugin.on_start(event)

            # Set callback and start HTTP plugin
            async def on_http_ready() -> None:
                self.log.info("Teams app started successfully")
                assert self._port is not None, "Port must be set before emitting start event"
                self._events.emit("start", StartEvent(port=self._port))

            self.http.on_ready_callback = on_http_ready
            event = PluginStartEvent(port=self._port)
            await self.http.on_start(event)

        except Exception as error:
            self._running = False
            self.log.error(f"Failed to start app: {error}")
            self._events.emit("error", ErrorEvent(error, context={"method": "start", "port": self._port}))
            raise

    async def stop(self) -> None:
        """Stop the Teams application."""
        if not self._running:
            return

        try:
            # Set callback and stop HTTP plugin first
            async def on_http_stopped() -> None:
                # Stop all other plugins after HTTP is stopped
                for plugin in reversed(self.plugins):
                    if plugin is not self.http:
                        await plugin.on_stop()

                self._running = False
                self.log.info("Teams app stopped")
                self._events.emit("stop", StopEvent())

            self.http.on_stopped_callback = on_http_stopped
            await self.http.on_stop()

        except Exception as error:
            self.log.error(f"Failed to stop app: {error}")
            self._events.emit("error", ErrorEvent(error, context={"method": "stop"}))
            raise

    def _init_credentials(self) -> Optional[Credentials]:
        """Initialize authentication credentials from options and environment."""
        client_id = self.options.client_id or os.getenv("CLIENT_ID")
        client_secret = self.options.client_secret or os.getenv("CLIENT_SECRET")
        tenant_id = self.options.tenant_id or os.getenv("TENANT_ID")

        self.log.debug(f"Using CLIENT_ID: {client_id}")
        if not tenant_id:
            self.log.warning("TENANT_ID is not set, assuming multi-tenant app")
        else:
            self.log.debug(f"Using TENANT_ID: {tenant_id} (assuming single-tenant app)")

        if client_id and client_secret:
            return ClientCredentials(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)

        return None

    async def _refresh_tokens(self, force: bool = False) -> None:
        """Refresh bot and graph tokens."""
        await asyncio.gather(self._refresh_bot_token(force), self._refresh_graph_token(force), return_exceptions=True)

    async def _refresh_bot_token(self, force: bool = False) -> None:
        """Refresh the bot authentication token."""
        if not self.credentials:
            self.log.warning("No credentials provided, skipping bot token refresh")
            return

        if not force and self._tokens.bot and not self._tokens.bot.is_expired():
            return

        if self._tokens.bot:
            self.log.debug("Refreshing bot token")

        try:
            token_response = await self.api.bots.token.get(self.credentials)
            self._tokens.bot = JsonWebToken(token_response.access_token)
            self.log.debug("Bot token refreshed successfully")

        except Exception as error:
            self.log.error(f"Failed to refresh bot token: {error}")

            self._events.emit("error", ErrorEvent(error, context={"method": "_refresh_bot_token"}))
            raise

    async def _refresh_graph_token(self, force: bool = False) -> None:
        """Refresh the Graph API token."""
        if not self.credentials:
            self.log.warning("No credentials provided, skipping bot token refresh")
            return

        if not force and self._tokens.graph and not self._tokens.graph.is_expired():
            return

        if self._tokens.graph:
            self.log.debug("Refreshing graph token")

        try:
            # TODO: Implement graph token refresh when graph client is available
            # token_response = await self.api.bots.token.get_graph(self.credentials)
            # self._tokens.graph = TokenProtocol(token_response.access_token)
            self.log.debug("Graph token refresh not yet implemented")

            # When implemented, emit token event:
        except Exception as error:
            self.log.error(f"Failed to refresh graph token: {error}")

            self._events.emit("error", ErrorEvent(error, context={"method": "_refresh_graph_token"}))
            raise

    async def handle_activity(self, input_activity: HttpActivityEvent) -> Dict[str, Any]:
        """
        Handle incoming activities using registered handlers and middleware chain.

        Args:
            activity: The Teams activity data

        Returns:
            Response data to send back
        """
        self.log.debug(f"Received activity: {input_activity}")

        activity = ActivityTypeAdapter.validate_python(input_activity.activity_payload)
        self.log.debug(f"Validated activity: {activity}")
        activity_type = activity.type
        activity_id = activity.id or ""

        self.log.info(f"Processing activity {activity_id} of type {activity_type}")

        try:
            self._events.emit("activity", ActivityEvent(activity))
            ctx = await self.build_context(activity, input_activity.token)
            response = await self._activity_processor.process_activity(ctx)
            await self.http.on_activity_response(
                PluginActivityResponseEvent(
                    conversation_ref=ctx.conversation_ref,
                    sender=self.http,
                    activity=activity,
                    response=response,
                ),
            )

            return {
                "status": "processed",
                "message": f"Successfully handled {activity_type} activity",
                "activityId": activity_id,
                "response": response,
            }
        except Exception as error:
            self.log.error(f"Failed to process activity {activity_id}: {error}")

            self._events.emit(
                "error",
                ErrorEvent(
                    error,
                    context={"method": "handle_activity", "activity_id": activity_id, "activity_type": activity_type},
                ),
            )
            raise

    async def build_context(self, activity: ActivityBase, token: TokenProtocol) -> ActivityContext[ActivityBase]:
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
                    connection_name=self.options.default_connection_name or "default",
                    user_id=activity.from_.id,
                    channel_id=activity.channel_id,
                )
            )
            user_token = JsonWebToken(user_token_res.token)
            is_signed_in = True
        except Exception:
            # User token not available
            pass

        return ActivityContext(
            activity,
            self.id or "",
            self.logger,
            self.storage,
            api_client,
            user_token,
            conversation_ref,
            is_signed_in,
            self.options.default_connection_name,
        )

    @overload
    def event(self, func_or_event_type: F) -> F:
        """Register event handler with auto-detected type from function signature."""
        ...

    @overload
    def event(self, func_or_event_type: Union[EventType, str]) -> Callable[[F], F]:
        """Register event handler with explicit event type."""
        ...

    @overload
    def event(self, func_or_event_type: None = None) -> Callable[[F], F]:
        """Register event handler (no arguments)."""
        ...

    def event(
        self,
        func_or_event_type: Union[F, EventType, str, None] = None,
    ) -> Union[F, Callable[[F], F]]:
        """
        Decorator to register event handlers with automatic type inference.

        Can be used in multiple ways:
        - @app.event (auto-detect from type hints)
        - @app.event("activity")

        Args:
            func_or_event_type: Either the function to decorate or an event type string
            event_type: Explicit event type (keyword-only)

        Returns:
            Decorated function or decorator

        Example:
            ```python
            @app.event
            async def handle_activity(event: ActivityEvent):
                print(f"Activity: {event.activity}")


            @app.event("error")
            async def handle_error(event: ErrorEvent):
                print(f"Error: {event.error}")
            ```
        """

        def decorator(func: F) -> F:
            detected_type = None

            # If event_type is provided, use it directly
            if isinstance(func_or_event_type, str):
                detected_type = func_or_event_type
            else:
                # Otherwise try to detect it from the function signature
                detected_type = get_event_type_from_signature(func)

            if not detected_type:
                raise ValueError(
                    f"Could not determine event type for {func.__name__}. "
                    "Either provide an explicit event_type or use a typed parameter."
                )

            # Validate the detected type against registered events
            if not is_registered_event(detected_type):
                raise ValueError(f"Event type '{detected_type}' is not registered. ")
            detected_type = cast(EventType, detected_type)

            # add it to the event emitter
            self._events.on(detected_type, func)
            return func

        # Check if the first argument is a callable function (direct decoration)
        if callable(func_or_event_type) and not isinstance(func_or_event_type, str):
            # Type narrow to ensure it's actually a function
            func: F = func_or_event_type  # type: ignore[assignment]
            return decorator(func)

        # Otherwise, return the decorator for later application
        return decorator

    def page(self, name: str, dir_path: str, page_path: Optional[str] = None) -> None:
        """
        Register a static page to serve at a specific path.

        Args:
            name: Unique name for the page
            dir_path: Directory containing the static files
            page_path: Optional path to serve the page at (defaults to /pages/{name})

        Example:
            ```python
            app.page("customform", os.path.join(os.path.dirname(__file__), "views", "customform"), "/tabs/dialog-form")
            ```
        """
        self.http.mount(name, dir_path, page_path=page_path)
