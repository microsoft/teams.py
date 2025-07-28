"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from logging import Logger
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, Optional

import uvicorn
from fastapi import FastAPI, Request
from microsoft.teams.api import TokenProtocol
from microsoft.teams.common.logging import ConsoleLogger

from .auth import create_jwt_validation_middleware


@dataclass
class HttpActivityEvent:
    activity_payload: Dict[str, Any]
    token: TokenProtocol


ActivityHandler = Callable[[HttpActivityEvent], Awaitable[Any]]


class HttpPlugin:
    """
    Basic HTTP plugin that provides a FastAPI server for Teams activities.
    """

    def __init__(
        self,
        app_id: Optional[str],
        logger: Optional[Logger] = None,
        enable_token_validation: bool = True,
        activity_handler: Optional[ActivityHandler] = None,
    ):
        self.logger = logger or ConsoleLogger().create_logger("@teams/http-plugin")
        self._server: Optional[uvicorn.Server] = None
        self._port: Optional[int] = None
        self._on_ready_callback: Optional[Callable[[], Awaitable[None]]] = None
        self._on_stopped_callback: Optional[Callable[[], Awaitable[None]]] = None

        # Storage for pending HTTP responses by activity ID
        self.pending: Dict[str, asyncio.Future[Any]] = {}

        # Activity handler for processing.
        # Once plugins work, this should be injected in.
        self.activity_handler = activity_handler

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

    async def on_start(self, port: int) -> None:
        """Start the HTTP server."""
        self._port = port

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

    def on_activity_response(self, activity_id: str, response_data: Any) -> None:
        """
        Complete a pending activity response.

        This is called when the App finishes processing an activity
        and is ready to send the HTTP response back.

        Args:
            activity_id: The ID of the activity to respond to
            response_data: The response data to send back
            plugin: The plugin that sent the response
        """
        future = self.pending.get(activity_id)
        if future and not future.done():
            future.set_result(response_data)
            self.logger.debug(f"Activity {activity_id} response completed")

        else:
            self.logger.warning(f"No pending future found for activity {activity_id}")

    def on_error(self, error: Exception, activity_id: Optional[str] = None) -> None:
        """
        Handle errors from the App.

        Args:
            error: The error that occurred
            activity_id: The ID of the activity that failed (if applicable)
            plugin: The plugin that caused the error (if applicable)
        """
        if activity_id:
            future = self.pending.get(activity_id)
            if future and not future.done():
                future.set_exception(error)
                self.logger.error(f"Activity {activity_id} failed: {error}")
            else:
                self.logger.warning(f"No pending future found for activity {activity_id} (error: {error})")
        else:
            self.logger.error(f"Plugin error: {error}")

    async def _process_activity(self, activity: Dict[str, Any], activity_id: str, token: TokenProtocol) -> None:
        """
        Process an activity via the registered handler.

        Args:
            activity: The Teams activity data
            token: The authorization token (if any)
            activity_id: The activity ID for response coordination
        """
        try:
            # Call the activity handler
            if self.activity_handler:
                event = HttpActivityEvent(activity, token)
                await self.activity_handler(event)
            else:
                self.on_activity_response(
                    activity_id,
                    {"status": "received", "message": "No handler registered"},
                )
        except Exception as error:
            # Complete with error
            self.on_error(error, activity_id)

    async def _on_activity(self, request: Request) -> Dict[str, Any]:
        """Handle incoming Teams activity."""
        body = await request.json()
        self.logger.info(f"Received activity: {body.get('type', 'unknown')}")

        # For now, just log and return success
        return {"status": "received"}

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
        if self.activity_handler:
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

        async def on_activity(request: Request) -> Any:
            """Handle incoming Teams activity."""
            # Process the activity (token validation handled by middleware)
            return await self._handle_activity_request(request)

        self.app.post("/api/messages")(on_activity)

        async def health_check() -> Dict[str, Any]:
            """Basic health check endpoint."""
            return {"status": "healthy", "port": self._port}

        self.app.get("/")(health_check)
