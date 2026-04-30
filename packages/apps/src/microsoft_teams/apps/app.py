"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import importlib.metadata
import logging
import os
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, TypeVar, Union, Unpack, cast, overload

from dependency_injector import providers
from dotenv import find_dotenv, load_dotenv
from microsoft_teams.api import (
    Account,
    ActivityBase,
    ActivityParams,
    ApiClient,
    ClientCredentials,
    ConversationAccount,
    ConversationReference,
    Credentials,
    FederatedIdentityCredentials,
    ManagedIdentityCredentials,
    MessageActivityInput,
    SentActivity,
    TokenCredentials,
    TokenProtocol,
)
from microsoft_teams.api.auth.cloud_environment import PUBLIC
from microsoft_teams.api.auth.cloud_environment import from_name as cloud_from_name
from microsoft_teams.cards import AdaptiveCard
from microsoft_teams.common import Client, ClientOptions, EventEmitter, LocalStorage

if TYPE_CHECKING:
    from msgraph.graph_service_client import GraphServiceClient

from .activity_sender import ActivitySender
from .app_events import EventManager
from .app_oauth import OauthHandlers
from .app_plugins import PluginProcessor
from .app_process import ActivityProcessor
from .auth import TokenValidator
from .auth.remote_function_jwt_middleware import validate_remote_function_request
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
from .http import FastAPIAdapter, HttpServer
from .http.adapter import HttpRequest, HttpResponse
from .options import AppOptions, InternalAppOptions
from .plugins import PluginBase, PluginStartEvent
from .routing import ActivityHandlerMixin, ActivityRouter
from .routing.activity_context import ActivityContext
from .token_manager import TokenManager
from .utils import create_graph_client
from .utils.thread import to_threaded_conversation_id

version = importlib.metadata.version("microsoft-teams-apps")

F = TypeVar("F", bound=Callable[..., Any])
FCtx = TypeVar("FCtx", bound=Callable[[FunctionContext[Any]], Any])
load_dotenv(find_dotenv(usecwd=True))

USER_AGENT = f"teams.py[apps]/{version}"

logger = logging.getLogger(__name__)


class App(ActivityHandlerMixin):
    """
    The main Teams application orchestrator.

    Manages plugins, tokens, and application lifecycle for Microsoft Teams apps.
    """

    def __init__(self, **options: Unpack[AppOptions]):
        self.options = InternalAppOptions.from_typeddict(options)

        # Resolve cloud environment from options or CLOUD env var
        cloud_env_name = os.getenv("CLOUD")
        self.cloud = self.options.cloud or (cloud_from_name(cloud_env_name) if cloud_env_name else PUBLIC)

        self.storage = self.options.storage or LocalStorage()

        self.http_client = self._init_http_client()

        self._events = EventEmitter[EventType]()
        self._router = ActivityRouter()

        self.credentials = self._init_credentials()

        self._token_manager = TokenManager(
            credentials=self.credentials,
            cloud=self.cloud,
        )

        self.container = Container()
        self.container.set_provider("id", providers.Object(self.id))
        self.container.set_provider("credentials", providers.Object(self.credentials))
        self.container.set_provider("bot_token", providers.Factory(lambda: self._get_bot_token))
        self.container.set_provider("storage", providers.Object(self.storage))
        self.container.set_provider(self.http_client.__class__.__name__, providers.Factory(lambda: self.http_client))

        service_url = (
            self.options.service_url or os.getenv("SERVICE_URL") or "https://smba.trafficmanager.net/teams"
        ).rstrip("/")

        self.api = ApiClient(
            service_url,
            self.http_client.clone(ClientOptions(token=self._get_bot_token)),
            self.options.api_client_settings,
            cloud=self.cloud,
        )

        plugins: List[PluginBase] = list(self.options.plugins)

        # Create HttpServer (not a plugin — owned directly by App)
        adapter = self.options.http_server_adapter or FastAPIAdapter()
        self.server = HttpServer(adapter, messaging_endpoint=self.options.messaging_endpoint)
        self.container.set_provider("HttpServer", providers.Object(self.server))

        self._port: Optional[int] = None
        self._initialized = False

        # initialize ActivitySender for sending activities
        self.activity_sender = ActivitySender(self.http_client.clone(ClientOptions(token=self._get_bot_token)))

        # initialize all event, activity, and plugin processors
        self.activity_processor = ActivityProcessor(
            self._router,
            self.id,
            self.storage,
            self.options.default_connection_name,
            self.http_client,
            self._token_manager,
            self.options.api_client_settings,
            self.activity_sender,
        )
        self.event_manager = EventManager(self._events)
        self.activity_processor.event_manager = self.event_manager
        self._plugin_processor = PluginProcessor(
            self.container, self.event_manager, self._events, self.activity_processor
        )
        self.plugins = self._plugin_processor.initialize_plugins(plugins)

        # default event handlers
        oauth_handlers = OauthHandlers(
            default_connection_name=self.options.default_connection_name,
            event_emitter=self._events,
        )
        self.on_signin_token_exchange(oauth_handlers.sign_in_token_exchange)
        self.on_signin_verify_state(oauth_handlers.sign_in_verify_state)
        self.on_signin_failure(oauth_handlers.sign_in_failure)

        self.entra_token_validator: Optional[TokenValidator] = None
        if self.credentials and hasattr(self.credentials, "client_id"):
            self.entra_token_validator = TokenValidator.for_entra(
                self.credentials.client_id,
                self.credentials.tenant_id,
                application_id_uri=self.options.application_id_uri,
                cloud=self.cloud,
            )

    @property
    def port(self) -> Optional[int]:
        """Port the app is running on."""
        return self._port

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
        """The app's ID from credentials."""
        if not self.credentials:
            return None
        return self.credentials.client_id

    async def initialize(self) -> None:
        """
        Initialize the Teams application without starting the HTTP server.

        This method sets up credentials, token manager, activity sender, and plugins,
        allowing you to use app.send() for proactive messaging without running a server.
        """
        if self._initialized:
            logger.warning("App is already initialized")
            return

        try:
            # Initialize plugins first (they may register routes, e.g. BotBuilder's /api/messages)
            for plugin in self.plugins:
                self._plugin_processor.inject(plugin)
                if hasattr(plugin, "on_init") and callable(plugin.on_init):
                    await plugin.on_init()

            # Initialize HttpServer (JWT validation + messaging endpoint route)
            self.server.on_request = self._process_activity_event
            self.server.initialize(
                credentials=self.credentials,
                skip_auth=self.options.skip_auth,
                cloud=self.cloud,
            )

            self._initialized = True
            logger.info("Teams app initialized successfully")

        except Exception as error:
            logger.error(f"Failed to initialize app: {error}")
            self._events.emit("error", ErrorEvent(error, context={"method": "initialize"}))
            raise

    async def _process_activity_event(self, event: Any) -> Any:
        """Process an activity event through the app pipeline. Used as HttpServer.on_request callback."""
        await self.event_manager.on_activity(event)
        return await self.activity_processor.process_activity(self.plugins, event)

    async def start(self, port: Optional[int] = None) -> None:
        """
        Start the Teams application and begin serving HTTP requests.

        This method will block and keep the application running until stopped.
        This is the main entry point for running your Teams app.

        Args:
            port: Port to listen on (defaults to PORT env var or 3978)
        """
        self._port = port or int(os.getenv("PORT", "3978"))

        try:
            # Initialize the app if not already initialized
            if not self._initialized:
                await self.initialize()

            # Start plugins and HTTP server concurrently (both may block with serve())
            tasks: List[Awaitable[Any]] = []
            event = PluginStartEvent(port=self._port)
            for plugin in self.plugins:
                is_callable = hasattr(plugin, "on_start") and callable(plugin.on_start)
                if is_callable:
                    tasks.append(plugin.on_start(event))

            logger.info("Teams app started successfully")
            self._events.emit("start", StartEvent(port=self._port))

            tasks.append(self.server.adapter.start(self._port))
            await asyncio.gather(*tasks)

        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("Teams app shutting down")
            try:
                await self._stop_plugins()
            finally:
                self._running = False
                self._events.emit("stop", StopEvent())

        except Exception as error:
            logger.error(f"Failed to start app: {error}")
            self._events.emit("error", ErrorEvent(error, context={"method": "start", "port": self._port}))
            raise

    async def stop(self) -> None:
        """Stop the Teams application."""
        try:
            # Stop HTTP server first
            await self.server.adapter.stop()

            # Stop all plugins
            for plugin in reversed(self.plugins):
                is_callable = hasattr(plugin, "on_stop") and callable(plugin.on_stop)
                if is_callable:
                    await plugin.on_stop()

            logger.info("Teams app stopped")
            self._events.emit("stop", StopEvent())

        except Exception as error:
            logger.error(f"Failed to stop app: {error}")
            self._events.emit("error", ErrorEvent(error, context={"method": "stop"}))
            raise

    async def send(self, conversation_id: str, activity: str | ActivityParams | AdaptiveCard):
        """Send an activity proactively to a conversation.

        Sends to the exact conversation ID provided. For channel threads,
        the conversation ID must include ``;messageid=`` - use :func:`to_threaded_conversation_id`
        to construct it, or use :meth:`reply` which handles this automatically.
        """

        if not self._initialized:
            raise ValueError("app not initialized - call app.initialize() or app.start() first")

        if self.id is None:
            raise ValueError("app credentials not configured")

        conversation_ref = ConversationReference(
            channel_id="msteams",
            service_url=self.api.service_url,
            bot=Account(id=self.id),
            conversation=ConversationAccount(id=conversation_id),
        )

        if isinstance(activity, str):
            activity = MessageActivityInput(text=activity)
        elif isinstance(activity, AdaptiveCard):
            activity = MessageActivityInput().add_card(activity)
        else:
            activity = activity

        return await self.activity_sender.send(activity, conversation_ref)

    @overload
    async def reply(
        self,
        conversation_id: str,
        message_id: str,
        activity: str | ActivityParams | AdaptiveCard,
    ) -> SentActivity: ...

    @overload
    async def reply(
        self,
        conversation_id: str,
        message_id: str | ActivityParams | AdaptiveCard,
    ) -> SentActivity: ...

    async def reply(  # type: ignore[reportInconsistentOverload]
        self,
        conversation_id: str,
        message_id: str | ActivityParams | AdaptiveCard = "",
        activity: str | ActivityParams | AdaptiveCard | None = None,
    ) -> SentActivity:
        """Send an activity proactively to a conversation, optionally as a threaded reply.

        **3-arg form** ``reply(conversation_id, message_id, activity)``:
        Constructs a threaded conversation ID via :func:`to_threaded_conversation_id`
        and sends to that thread. The service determines whether threading is
        supported for the given conversation type.

        **2-arg form** ``reply(conversation_id, activity)``:
        Sends to the exact conversation ID provided - threaded if it contains
        ``;messageid=``, flat otherwise.

        Args:
            conversation_id: The conversation ID
            message_id: The thread root message ID (3-arg form) or the activity (2-arg form)
            activity: The activity to send (only in 3-arg form)
        """
        if activity is not None:
            if not isinstance(message_id, str):
                raise TypeError("message_id must be a string when activity is provided")
            return await self.send(to_threaded_conversation_id(conversation_id, message_id), activity)

        return await self.send(conversation_id, message_id)

    def use(self, middleware: Callable[[ActivityContext[ActivityBase]], Awaitable[None]]) -> None:
        """Add middleware to run on all activities."""
        self.router.add_handler(lambda _: True, middleware)

    def _init_http_client(self) -> Client:
        """Initialize the HTTP client from options or create a default one.

        Always injects the app's User-Agent header.
        """
        client_opt = self.options.client
        if isinstance(client_opt, Client):
            return client_opt.clone(ClientOptions(headers={"User-Agent": USER_AGENT}))
        if isinstance(client_opt, ClientOptions):
            merged_headers = {**client_opt.headers, "User-Agent": USER_AGENT}
            return Client(
                ClientOptions(
                    base_url=client_opt.base_url,
                    headers=merged_headers,
                    timeout=client_opt.timeout,
                    token=client_opt.token,
                    interceptors=client_opt.interceptors,
                )
            )
        return Client(ClientOptions(headers={"User-Agent": USER_AGENT}))

    def _init_credentials(self) -> Optional[Credentials]:
        """Initialize authentication credentials from options and environment."""
        client_id = self.options.client_id or os.getenv("CLIENT_ID")
        client_secret = self.options.client_secret or os.getenv("CLIENT_SECRET")
        tenant_id = self.options.tenant_id or os.getenv("TENANT_ID")
        token = self.options.token
        managed_identity_client_id = self.options.managed_identity_client_id or os.getenv("MANAGED_IDENTITY_CLIENT_ID")

        logger.debug(f"Using CLIENT_ID: {client_id}")
        if not tenant_id:
            logger.warning("TENANT_ID is not set, assuming multi-tenant app")
        else:
            logger.debug(f"Using TENANT_ID: {tenant_id} (assuming single-tenant app)")

        if client_id and client_secret:
            logger.debug("Using client secret for auth")
            return ClientCredentials(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)

        if client_id and token:
            return TokenCredentials(client_id=client_id, tenant_id=tenant_id, token=token)

        if client_id:
            if managed_identity_client_id == "system":
                logger.debug("Using Federated Identity Credentials with system-assigned managed identity")
                return FederatedIdentityCredentials(
                    client_id=client_id,
                    managed_identity_type="system",
                    managed_identity_client_id=None,
                    tenant_id=tenant_id,
                )

            if managed_identity_client_id and managed_identity_client_id != client_id:
                logger.debug("Using Federated Identity Credentials with user-assigned managed identity")
                return FederatedIdentityCredentials(
                    client_id=client_id,
                    managed_identity_type="user",
                    managed_identity_client_id=managed_identity_client_id,
                    tenant_id=tenant_id,
                )

            logger.debug("Using user-assigned managed identity (direct)")
            mi_client_id = managed_identity_client_id or client_id
            return ManagedIdentityCredentials(
                client_id=mi_client_id,
                tenant_id=tenant_id,
            )

        return None

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

            # Validate the detected type against registered events or custom event
            if not is_registered_event(detected_type):
                logger.info(f"Event type '{detected_type}' is not a registered type.")
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
        self.server.adapter.serve_static(page_path or f"/{name}", dir_path)

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
            logger.debug("Generated endpoint name for function '%s': %s", func.__name__, endpoint_name)

            async def handler(request: HttpRequest) -> HttpResponse:
                client_context, error = await validate_remote_function_request(
                    request["headers"], self.entra_token_validator
                )
                if error or not client_context:
                    return HttpResponse(status=401, body={"detail": error or "unauthorized"})

                ctx = FunctionContext(
                    id=self.id,
                    api=self.api,
                    activity_sender=self.activity_sender,
                    data=request["body"],
                    **client_context.__dict__,
                )
                result = await func(ctx)
                return HttpResponse(status=200, body=result)

            self.server.adapter.register_route("POST", f"/api/functions/{endpoint_name}", handler)
            return func

        # Direct decoration: @app.func
        if callable(name_or_func) and not isinstance(name_or_func, str):
            return decorator(name_or_func)

        # Named decoration: @app.func("name")
        return decorator

    async def _stop_plugins(self) -> None:
        for plugin in reversed(self.plugins):
            if hasattr(plugin, "on_stop") and callable(plugin.on_stop):
                await plugin.on_stop()

    async def _get_bot_token(self):
        return await self._token_manager.get_bot_token()

    async def _get_graph_token(self, tenant_id: Optional[str] = None) -> Optional[TokenProtocol]:
        return await self._token_manager.get_graph_token(tenant_id)

    def get_app_graph(self, tenant_id: Optional[str] = None) -> "GraphServiceClient":
        """
        Get a Microsoft Graph client configured with the app's token.

        This client can be used for app-only operations that don't require user context.
        For multi-tenant apps, pass a tenant_id to get a tenant-specific token.

        Args:
            tenant_id: Optional tenant ID. If not provided, uses the app's default tenant.

        Raises:
            ImportError: If the graph dependencies are not installed.

        """
        return create_graph_client(lambda: self._get_graph_token(tenant_id))
