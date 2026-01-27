"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import importlib.metadata
from contextlib import AsyncExitStack, asynccontextmanager
from logging import Logger
from pathlib import Path
from types import SimpleNamespace
from typing import (
    Annotated,
    Any,
    AsyncGenerator,
    Awaitable,
    Callable,
    Dict,
    Optional,
    TypedDict,
    Union,
    Unpack,
    cast,
)

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from microsoft_teams.api import (
    Credentials,
    InvokeResponse,
    TokenProtocol,
)
from microsoft_teams.common import ConsoleLogger
from pydantic import BaseModel
from starlette.applications import Starlette
from starlette.types import Lifespan

from .auth import create_jwt_validation_middleware
from .events import ActivityEvent, CoreActivity, ErrorEvent
from .plugins import (
    DependencyMetadata,
    EventMetadata,
    LoggerDependencyOptions,
    PluginActivityResponseEvent,
    PluginBase,
    PluginStartEvent,
)
from .plugins.metadata import Plugin

version = importlib.metadata.version("microsoft-teams-apps")


class HttpPluginOptions(TypedDict, total=False):
    """Options for configuring the HTTP plugin."""

    logger: Logger
    skip_auth: bool
    server_factory: Callable[[FastAPI], uvicorn.Server]


@Plugin(name="http", version=version, description="the default plugin for receiving activities via HTTP")
class HttpPlugin(PluginBase):
    """
    Basic HTTP plugin that provides a FastAPI server for Teams activities.
    Handles HTTP server setup, routing, and authentication.
    """

    logger: Annotated[Logger, LoggerDependencyOptions()]
    credentials: Annotated[Optional[Credentials], DependencyMetadata(optional=True)]

    on_error_event: Annotated[Callable[[ErrorEvent], None], EventMetadata(name="error")]
    on_activity_event: Annotated[Callable[[ActivityEvent], InvokeResponse[Any]], EventMetadata(name="activity")]

    lifespans: list[Lifespan[Starlette]] = []

    def __init__(self, **options: Unpack[HttpPluginOptions]):
        """
        Args:
            logger: Optional logger.
            skip_auth: Whether to skip JWT validation.
            server_factory: Optional function that takes an ASGI app
                and returns a configured `uvicorn.Server`.
            Example:
                ```python
                def custom_server_factory(app: FastAPI) -> uvicorn.Server:
                    return uvicorn.Server(config=uvicorn.Config(app, host="0.0.0.0", port=8000))


                http_plugin = HttpPlugin(server_factory=custom_server_factory)
                ```
        """
        super().__init__()
        self.logger = options.get("logger") or ConsoleLogger().create_logger("@teams/http-plugin")
        self._port: Optional[int] = None
        self._skip_auth: bool = options.get("skip_auth", False)
        self._server: Optional[uvicorn.Server] = None
        self._on_ready_callback: Optional[Callable[[], Awaitable[None]]] = None
        self._on_stopped_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Setup FastAPI app with lifespan
        @asynccontextmanager
        async def default_lifespan(_app: Starlette) -> AsyncGenerator[None, None]:
            # Startup
            self.logger.info(f"listening on port {self._port} 🚀")
            if self._on_ready_callback:
                await self._on_ready_callback()
            yield
            # Shutdown
            self.logger.info("Server shutting down")
            if self._on_stopped_callback:
                await self._on_stopped_callback()

        @asynccontextmanager
        async def combined_lifespan(app: Starlette):
            async with AsyncExitStack() as stack:
                lifespans = self.lifespans.copy()
                lifespans.append(default_lifespan)
                for lifespan in lifespans:
                    await stack.enter_async_context(lifespan(app))
                yield

        self.app = FastAPI(lifespan=combined_lifespan)

        # Create uvicorn server if user provides custom factory method
        server_factory = options.get("server_factory")
        if server_factory:
            self._server = server_factory(self.app)
            if self._server.config.app is not self.app:
                raise ValueError(
                    "server_factory must return a uvicorn.Server configured with the provided FastAPI app instance."
                )

        # Expose FastAPI routing methods (like TypeScript exposes Express methods)
        self.get = self.app.get
        self.post = self.app.post
        self.put = self.app.put
        self.patch = self.app.patch
        self.delete = self.app.delete
        self.middleware = self.app.middleware

        # Setup routes and error handlers
        self._setup_routes()

    @property
    def on_ready_callback(self) -> Optional[Callable[[], Awaitable[None]]]:
        """Callback to call when HTTP server is ready."""
        return self._on_ready_callback

    @on_ready_callback.setter
    def on_ready_callback(self, callback: Optional[Callable[[], Awaitable[None]]]) -> None:
        """Set callback to call when HTTP server is ready."""
        self._on_ready_callback = callback

    @property
    def on_stopped_callback(self) -> Optional[Callable[[], Awaitable[None]]]:
        """Callback to call when HTTP server is stopped."""
        return self._on_stopped_callback

    @on_stopped_callback.setter
    def on_stopped_callback(self, callback: Optional[Callable[[], Awaitable[None]]]) -> None:
        """Set callback to call when HTTP server is stopped."""
        self._on_stopped_callback = callback

    async def on_init(self) -> None:
        """
        Initialize the HTTP plugin when the app starts.
        This adds JWT validation middleware unless `skip_auth` is True.
        """

        # Add JWT validation middleware
        app_id = getattr(self.credentials, "client_id", None)
        if app_id and not self._skip_auth:
            jwt_middleware = create_jwt_validation_middleware(
                app_id=app_id, logger=self.logger, paths=["/api/messages"]
            )
            self.app.middleware("http")(jwt_middleware)

    async def on_start(self, event: PluginStartEvent) -> None:
        """Start the HTTP server."""
        self._port = event.port

        try:
            if self._server and self._server.config.port != self._port:
                self.logger.warning(
                    "Using port configured by server factory: %d, but plugin start event has port %d.",
                    self._server.config.port,
                    self._port,
                )
                self._port = self._server.config.port
            else:
                config = uvicorn.Config(app=self.app, host="0.0.0.0", port=self._port, log_level="info")
                self._server = uvicorn.Server(config)

            self.logger.info("Starting HTTP server on port %d", self._port)

            # The lifespan handler will call the callback when the server is ready
            await self._server.serve()

        except OSError as error:
            # Handle port in use, permission errors, etc.
            self.logger.error("Server startup failed: %s", error)
            raise
        except Exception as error:
            self.logger.error("Failed to start server: %s", error)
            raise

    async def on_stop(self) -> None:
        """Stop the HTTP server."""
        if self._server:
            self.logger.info("Stopping HTTP server")
            self._server.should_exit = True

    async def on_activity_response(self, event: PluginActivityResponseEvent) -> None:
        """
        Complete a pending activity response.

        This is called when the App finishes processing an activity
        and is ready to send the HTTP response back.

        Args:
            activity_id: The ID of the activity to respond to
            response_data: The response data to send back
            plugin: The plugin that sent the response
        """
        self.logger.debug(f"Completing activity response for {event.activity.id}")

    async def _process_activity(self, core_activity: CoreActivity, token: TokenProtocol) -> InvokeResponse[Any]:
        """
        Process an activity via the registered handler.

        Args:
            core_activity: The core activity payload
            token: The authorization token (if any)
        """
        result: InvokeResponse[Any]
        try:
            event = ActivityEvent(body=core_activity, token=token)
            if asyncio.iscoroutinefunction(self.on_activity_event):
                result = await self.on_activity_event(event)
            else:
                result = self.on_activity_event(event)
        except Exception as error:
            # Log with full traceback
            self.logger.exception(str(error))
            result = InvokeResponse(status=500)

        return result

    def _handle_activity_response(self, response: Response, result: Any) -> Union[Response, Dict[str, object]]:
        """
        Handle the activity response formatting.

        Args:
            response: The FastAPI response object
            result: The result from activity processing

        Returns:
            The formatted response
        """
        status_code: Optional[int] = None
        body: Optional[Dict[str, Any]] = None
        resp_dict: Optional[Dict[str, Any]] = None
        if isinstance(result, dict):
            resp_dict = cast(Dict[str, Any], result)
        elif isinstance(result, BaseModel):
            resp_dict = result.model_dump(exclude_none=True)

        # if resp_dict has status set it
        if resp_dict and "status" in resp_dict:
            status_code = resp_dict.get("status")

        if resp_dict and "body" in resp_dict:
            body = resp_dict.get("body", None)

        if status_code is not None:
            response.status_code = status_code

        if body is not None:
            self.logger.debug(f"Returning body {body}")
            return body
        self.logger.debug("Returning empty body")
        return response

    async def on_activity_request(self, core_activity: CoreActivity, request: Request, response: Response) -> Any:
        """Handle incoming Teams activity."""
        # Get validated token from middleware (if present - will be missing if skip_auth is True)
        if hasattr(request.state, "validated_token") and request.state.validated_token:
            token = request.state.validated_token
        else:
            token = cast(
                TokenProtocol,
                SimpleNamespace(
                    app_id="",
                    app_display_name="",
                    tenant_id="",
                    service_url=core_activity.service_url or "",
                    from_="azure",
                    from_id="",
                    is_expired=lambda: False,
                ),
            )

        activity_type = core_activity.type or "unknown"
        activity_id = core_activity.id or "unknown"

        self.logger.debug(f"Received activity: {activity_type} (ID: {activity_id})")
        self.logger.debug(f"Processing activity {activity_id} via handler...")

        # Process the activity
        result = await self._process_activity(core_activity, token)
        return self._handle_activity_response(response, result)

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        self.app.post("/api/messages")(self.on_activity_request)

        async def health_check() -> Dict[str, Any]:
            """Basic health check endpoint."""
            return {"status": "healthy", "port": self._port}

        self.app.get("/")(health_check)

    def mount(self, name: str, dir_path: Path | str, page_path: Optional[str] = None) -> None:
        """
        Serve a static page at the given path.

        Args:
            name: The name of the page (used in URL)
            page_path: The path to the static HTML file
        """
        self.app.mount(page_path or f"/{name}", StaticFiles(directory=dir_path, check_dir=True, html=True), name=name)
