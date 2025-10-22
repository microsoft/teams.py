"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import importlib.metadata
import os
from logging import Logger
from typing import Any, Awaitable, Callable, List, Optional, TypeVar, Union, Unpack, cast, overload

from dependency_injector import providers
from dotenv import find_dotenv, load_dotenv
from fastapi import Request
from microsoft.teams.api import (
    Account,
    ActivityBase,
    ActivityParams,
    ApiClient,
    ClientCredentials,
    ConversationAccount,
    ConversationReference,
    Credentials,
    JsonWebToken,
    MessageActivityInput,
    TokenCredentials,
)
from microsoft.teams.cards import AdaptiveCard
from microsoft.teams.common import Client, ClientOptions, ConsoleLogger, EventEmitter, LocalStorage

from .app_events import EventManager
from .app_oauth import OauthHandlers
from .app_plugins import PluginProcessor
from .app_process import ActivityProcessor
from .app_tokens import AppTokens
from .auth import TokenValidator
from .auth.remote_function_jwt_middleware import remote_function_jwt_validation
from .container import Container
from .contexts.function_context import FunctionContext
from .events import (
    ErrorEvent,
    EventType,
    StartEvent,
    StopEvent,
    get_event_type_from_signature,
    is_registered_event,
)
from .graph_token_manager import GraphTokenManager
from .http_plugin import HttpPlugin
from .options import AppOptions, InternalAppOptions
from .plugins import PluginBase, PluginStartEvent, get_metadata
from .routing import ActivityHandlerMixin, ActivityRouter
from .routing.activity_context import ActivityContext

version = importlib.metadata.version("microsoft-teams-apps")

F = TypeVar("F", bound=Callable[..., Any])
FCtx = TypeVar("FCtx", bound=Callable[[FunctionContext[Any]], Any])
load_dotenv(find_dotenv(usecwd=True))

USER_AGENT = f"teams.py[app]/{version}"


class App(ActivityHandlerMixin):
    """
    The main Teams application orchestrator.

    Manages plugins, tokens, and application lifecycle for Microsoft Teams apps.
    """

    def __init__(self, **options: Unpack[AppOptions]):
        self.options = InternalAppOptions.from_typeddict(options)

        self.log = self.options.logger or ConsoleLogger().create_logger("@teams/app")
        self.storage = self.options.storage or LocalStorage()

        self.http_client = Client(
            ClientOptions(
                headers={"User-Agent": USER_AGENT},
            )
        )

        self._events = EventEmitter[EventType]()
        self._router = ActivityRouter()

        self._tokens = AppTokens()
        self.credentials = self._init_credentials()

        self.container = Container()
        self.container.set_provider("id", providers.Object(self.id))
        self.container.set_provider("name", providers.Object(self.name))
        self.container.set_provider("credentials", providers.Object(self.credentials))
        self.container.set_provider("bot_token", providers.Callable(lambda: self.tokens.bot))
        self.container.set_provider("graph_token", providers.Callable(lambda: self.tokens.graph))
        self.container.set_provider("logger", providers.Object(self.log))
        self.container.set_provider("storage", providers.Object(self.storage))
        self.container.set_provider(self.http_client.__class__.__name__, providers.Factory(lambda: self.http_client))

        self.api = ApiClient(
            "https://smba.trafficmanager.net/teams",
            self.http_client.clone(ClientOptions(token=lambda: self.tokens.bot)),
        )

        plugins: List[PluginBase] = list(self.options.plugins)

        http_plugin = None
        for i, plugin in enumerate(plugins):
            meta = get_metadata(type(plugin))
            if meta.name == "http":
                http_plugin = plugin
                plugins.pop(i)
                break

        if not http_plugin:
            app_id = None
            if self.credentials and hasattr(self.credentials, "client_id"):
                app_id = self.credentials.client_id

            http_plugin = HttpPlugin(app_id, self.log, self.options.skip_auth)

        plugins.insert(0, http_plugin)
        self.http = cast(HttpPlugin, http_plugin)

        self._port: Optional[int] = None
        self._running = False

        # initialize all event, activity, and plugin processors
        self.graph_token_manager = GraphTokenManager(
            api_client=self.api,
            credentials=self.credentials,
            logger=self.log,
        )
        self.activity_processor = ActivityProcessor(
            self._router,
            self.log,
            self.id,
            self.storage,
            self.options.default_connection_name,
            self.http_client,
            self.tokens,
            self.graph_token_manager,
        )
        self.event_manager = EventManager(self._events, self.activity_processor)
        self.activity_processor.event_manager = self.event_manager
        self._plugin_processor = PluginProcessor(self.container, self.event_manager, self.log, self._events)
        self.plugins = self._plugin_processor.initialize_plugins(plugins)

        # default event handlers
        oauth_handlers = OauthHandlers(
            default_connection_name=self.options.default_connection_name,
            event_emitter=self._events,
        )
        self.on_signin_token_exchange(oauth_handlers.sign_in_token_exchange)
        self.on_signin_verify_state(oauth_handlers.sign_in_verify_state)

        self.entra_token_validator: Optional[TokenValidator] = None
        if self.credentials and hasattr(self.credentials, "client_id"):
            self.entra_token_validator = TokenValidator.for_entra(
                self.credentials.client_id, self.credentials.tenant_id, logger=self.log
            )

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
        return (
            self._tokens.bot.app_id if self._tokens.bot else self._tokens.graph.app_id if self._tokens.graph else None
        )

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

            for plugin in self.plugins:
                # Inject the dependencies
                self._plugin_processor.inject(plugin)
                if hasattr(plugin, "on_init") and callable(plugin.on_init):
                    await plugin.on_init()

            # Set callback and start HTTP plugin
            async def on_http_ready() -> None:
                self.log.info("Teams app started successfully")
                assert self._port is not None, "Port must be set before emitting start event"
                self._events.emit("start", StartEvent(port=self._port))

            self.http.on_ready_callback = on_http_ready

            tasks: List[Awaitable[Any]] = []
            event = PluginStartEvent(port=self._port)
            for plugin in self.plugins:
                is_callable = hasattr(plugin, "on_start") and callable(plugin.on_start)
                if is_callable:
                    tasks.append(plugin.on_start(event))
            await asyncio.gather(*tasks)

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
                    is_callable = hasattr(plugin, "on_stop") and callable(plugin.on_stop)
                    if plugin is not self.http and is_callable:
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

    async def send(self, conversation_id: str, activity: str | ActivityParams | AdaptiveCard):
        """Send an activity proactively."""

        if self.id is None or self.name is None:
            raise ValueError("app not started")

        conversation_ref = ConversationReference(
            channel_id="msteams",
            service_url=self.api.service_url,
            bot=Account(id=self.id, name=self.name, role="bot"),
            conversation=ConversationAccount(id=conversation_id, conversation_type="personal"),
        )

        if isinstance(activity, str):
            activity = MessageActivityInput(text=activity)
        elif isinstance(activity, AdaptiveCard):
            activity = MessageActivityInput().add_card(activity)
        else:
            activity = activity

        return await self.http.send(activity, conversation_ref)

    def use(self, middleware: Callable[[ActivityContext[ActivityBase]], Awaitable[None]]) -> None:
        """Add middleware to run on all activities."""
        self.router.add_handler(lambda _: True, middleware)

    def _init_credentials(self) -> Optional[Credentials]:
        """Initialize authentication credentials from options and environment."""
        client_id = self.options.client_id or os.getenv("CLIENT_ID")
        client_secret = self.options.client_secret or os.getenv("CLIENT_SECRET")
        tenant_id = self.options.tenant_id or os.getenv("TENANT_ID")
        token = self.options.token

        self.log.debug(f"Using CLIENT_ID: {client_id}")
        if not tenant_id:
            self.log.warning("TENANT_ID is not set, assuming multi-tenant app")
        else:
            self.log.debug(f"Using TENANT_ID: {tenant_id} (assuming single-tenant app)")

        # - If client_id + client_secret : use ClientCredentials (standard client auth)
        if client_id and client_secret:
            return ClientCredentials(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)

        # - If client_id + token callable : use TokenCredentials (where token is a custom token provider)
        if client_id and token:
            return TokenCredentials(client_id=client_id, tenant_id=tenant_id, token=token)

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
            self.log.warning("No credentials provided, skipping graph token refresh")
            return

        if not force and self._tokens.graph and not self._tokens.graph.is_expired():
            return

        if self._tokens.graph:
            self.log.debug("Refreshing graph token")

        try:
            # Use GraphTokenManager for tenant-aware token management
            tenant_id = self.credentials.tenant_id if self.credentials else None
            token = await self.graph_token_manager.get_token(tenant_id)

            if token:
                self._tokens.graph = token
                self.log.debug("Graph token refreshed successfully")

                # Emit token acquired event
                self._events.emit("token", {"type": "graph", "token": self._tokens.graph})
            else:
                self.log.debug("Failed to get graph token from GraphTokenManager")

        except Exception as error:
            self.log.error(f"Failed to refresh graph token: {error}")

            self._events.emit("error", ErrorEvent(error, context={"method": "_refresh_graph_token"}))
            raise

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

    def tab(self, name: str, path: str) -> None:
        """
        Add/update a static tab.
        The tab will be hosted at
        http://localhost:<PORT>/tabs/<name> or https://<BOT_DOMAIN>/tabs/<name>
        Scopes default to 'personal'.

        Args:
            name A unique identifier for the entity which the tab displays.
            path The path to the directory containing the tab's content (HTML, JS, CSS, etc.)
        """
        self.page(name, dir_path=path, page_path=f"/tabs/{name}/")

    def func(self, name_or_func: Union[str, FCtx, None] = None) -> Union[FCtx, Callable[[FCtx], FCtx]]:
        """
        Decorator that registers a function as a remotely callable endpoint.

        Args:
            name_or_func:
            - str: explicit name for the endpoint
            - Callable: directly decorating the function, endpoint name defaults to the function's name

        Example:
            ```python
            @app.func
            async def post_to_chat(ctx: FunctionContext[Any]):
                await ctx.send(ctx.data["message"])
            ```
        """

        def decorator(func: FCtx) -> FCtx:
            endpoint_name = name_or_func if isinstance(name_or_func, str) else func.__name__.replace("_", "-")
            self.logger.debug("Generated endpoint name for function '%s': %s", func.__name__, endpoint_name)

            async def endpoint(req: Request):
                middleware = remote_function_jwt_validation(self.log, self.entra_token_validator)

                async def call_next(r: Request) -> Any:
                    ctx = FunctionContext(
                        id=self.id,
                        name=self.name,
                        api=self.api,
                        http=self.http,
                        log=self.log,
                        data=await r.json(),
                        **r.state.context.__dict__,
                    )
                    return await func(ctx)

                return await middleware(req, call_next)

            self.http.post(f"/api/functions/{endpoint_name}")(endpoint)
            return func

        # Direct decoration: @app.func
        if callable(name_or_func) and not isinstance(name_or_func, str):
            return decorator(name_or_func)

        # Named decoration: @app.func("name")
        return decorator
