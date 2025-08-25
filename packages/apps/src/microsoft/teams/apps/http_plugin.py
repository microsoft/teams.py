"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import importlib.metadata
from contextlib import asynccontextmanager
from logging import Logger
from pathlib import Path
from typing import Annotated, Any, AsyncGenerator, Awaitable, Callable, Dict, Optional, cast

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from microsoft.teams.api import Activity, ActivityParams, ApiClient, ConversationReference, SentActivity, TokenProtocol
from microsoft.teams.common.http.client import Client, ClientOptions
from microsoft.teams.common.logging import ConsoleLogger
from pydantic import BaseModel

from .auth import create_jwt_validation_middleware
from .events import ActivityEvent, ErrorEvent
from .plugins import (
    DependencyMetadata,
    EventMetadata,
    LoggerDependencyOptions,
    PluginActivityResponseEvent,
    PluginErrorEvent,
    PluginStartEvent,
    Sender,
    StreamerProtocol,
)
from .plugins.metadata import Plugin

version = importlib.metadata.version("microsoft-teams-apps")


@Plugin(name="http", version=version, description="the default plugin for sending/receiving activities")
class HttpPlugin(Sender):
    """
    Basic HTTP plugin that provides a FastAPI server for Teams activities.
    """

    logger: Annotated[Logger, LoggerDependencyOptions()]

    on_error_event: Annotated[Callable[[ErrorEvent], None], EventMetadata(name="error")]
    on_activity_event: Annotated[Callable[[ActivityEvent], None], EventMetadata(name="activity")]

    client: Annotated[Client, DependencyMetadata()]

    bot_token: Annotated[Optional[Callable[[], TokenProtocol]], DependencyMetadata(optional=True)]
    graph_token: Annotated[Optional[Callable[[], TokenProtocol]], DependencyMetadata(optional=True)]

    def __init__(
        self,
        app_id: Optional[str],
        logger: Optional[Logger] = None,
        enable_token_validation: bool = True,
    ):
        super().__init__()
        self.logger = logger or ConsoleLogger().create_logger("@teams/http-plugin")
        self._server: Optional[uvicorn.Server] = None
        self._port: Optional[int] = None
        self._on_ready_callback: Optional[Callable[[], Awaitable[None]]] = None
        self._on_stopped_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Storage for pending HTTP responses by activity ID
        self.pending: Dict[str, asyncio.Future[Any]] = {}

        # Setup FastAPI app with lifespan
        @asynccontextmanager
        async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
            # Startup
            self.logger.info(f"listening on port {self._port} 🚀")
            if self._on_ready_callback:
                await self._on_ready_callback()
            yield
            # Shutdown
            self.logger.info("Server shutting down")
            if self._on_stopped_callback:
                await self._on_stopped_callback()

        self.app = FastAPI(lifespan=lifespan)

        # Add JWT validation middleware
        if app_id and enable_token_validation:
            jwt_middleware = create_jwt_validation_middleware(
                app_id=app_id, logger=self.logger, paths=["/api/messages"]
            )
            self.app.middleware("http")(jwt_middleware)

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

    async def on_start(self, event: PluginStartEvent) -> None:
        """Start the HTTP server."""
        port = event.port
        self._port = event.port

        try:
            config = uvicorn.Config(app=self.app, host="0.0.0.0", port=port, log_level="info")
            self._server = uvicorn.Server(config)

            self.logger.info("Starting HTTP server on port %d", port)

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
        future = self.pending.get(event.activity.id)
        if future and not future.done():
            future.set_result(event.response)

        else:
            self.logger.warning(f"No pending future found for activity {event.activity.id}")

    async def on_error(self, event: PluginErrorEvent) -> None:
        """
        Handle errors from the App.

        Args:
            error: The error that occurred
            activity_id: The ID of the activity that failed (if applicable)
            plugin: The plugin that caused the error (if applicable)
        """
        activity_id = event.activity.id if event.activity else None
        error = event.error
        if activity_id:
            future = self.pending.get(activity_id)
            if future and not future.done():
                future.set_exception(error)
                self.logger.error(f"Activity {activity_id} failed: {error}")
            else:
                self.logger.warning(f"No pending future found for activity {activity_id} (error: {error})")
        else:
            self.logger.error(f"Plugin error: {error}")

    async def send(self, activity: ActivityParams, ref: ConversationReference) -> SentActivity:
        api = ApiClient(service_url=ref.service_url, options=self.client.clone(ClientOptions(token=self.bot_token)))

        activity.from_ = ref.bot
        activity.conversation = ref.conversation

        if activity.id:
            res = await api.conversations.activities(ref.conversation.id).update(activity.id, activity)
            return SentActivity.merge(activity, res)

        res = await api.conversations.activities(ref.conversation.id).create(activity)
        return SentActivity.merge(activity, res)

    async def _process_activity(self, activity: Activity, activity_id: str, token: TokenProtocol) -> None:
        """
        Process an activity via the registered handler.

        Args:
            activity: The Teams activity data
            token: The authorization token (if any)
            activity_id: The activity ID for response coordination
        """
        try:
            if callable(self.on_activity):
                event = ActivityEvent(activity=activity, sender=self, token=token)
                self.on_activity_event(event)
            else:
                await self.on_error(
                    PluginErrorEvent(sender=self, error=Exception("No activity handler registered"), activity=activity)
                )
        except Exception as error:
            # Complete with error
            await self.on_error(PluginErrorEvent(sender=self, error=error, activity=activity))

    async def _handle_activity_request(self, request: Request) -> Any:
        """
        Process the activity request and coordinate response.

        Args:
            request: The FastAPI request object (token is in request.state.validated_token)

        Returns:
            The activity processing result
        """
        # Get validated token from middleware (always present if middleware is active)
        token = getattr(request.state, "validated_token", None)
        if not token or not isinstance(token, TokenProtocol):
            self.logger.error("No valid token found in request state")
            return {"error": "Unauthorized", "status": 401}

        # Parse activity data
        body = await request.json()
        activity_type = body.get("type", "unknown")
        activity_id = body.get("id", "unknown")

        self.logger.info(f"Received activity: {activity_type} (ID: {activity_id})")

        # Create Future for async response coordination
        response_future = asyncio.get_event_loop().create_future()
        self.pending[activity_id] = response_future

        # Fire activity processing via callback
        if callable(self.on_activity_event):
            try:
                # Call the activity handler asynchronously
                self.logger.debug(f"Processing activity {activity_id} via handler...")
                asyncio.create_task(self._process_activity(body, activity_id, token))
            except Exception as error:
                self.logger.error(f"Failed to start activity processing: {error}")
                response_future.set_exception(error)
        else:
            # No handler - just complete with placeholder
            self.logger.debug("No activity handler - returning placeholder response")
            response_future.set_result({"status": "received"})

        # Wait for the activity processing to complete
        result = await response_future

        # Clean up
        if activity_id in self.pending:
            del self.pending[activity_id]

        return result

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        async def on_activity_request(request: Request, response: Response) -> Any:
            """Handle incoming Teams activity."""
            # Process the activity (token validation handled by middleware)
            result = await self._handle_activity_request(request)
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
                return body
            return cast(Any, result)

        self.app.post("/api/messages")(on_activity_request)

        async def health_check() -> Dict[str, Any]:
            """Basic health check endpoint."""
            return {"status": "healthy", "port": self._port}

        self.app.get("/")(health_check)

    async def create_stream(self, ref: ConversationReference) -> StreamerProtocol:
        raise NotImplementedError

    def mount(self, name: str, dir_path: Path | str, page_path: Optional[str] = None) -> None:
        """
        Serve a static page at the given path.

        Args:
            name: The name of the page (used in URL)
            page_path: The path to the static HTML file
        """
        self.app.mount(page_path or f"/{name}", StaticFiles(directory=dir_path, check_dir=True, html=True), name=name)
