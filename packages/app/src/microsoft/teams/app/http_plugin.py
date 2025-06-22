"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
from contextlib import asynccontextmanager
from logging import Logger
from typing import Any, Callable, Dict, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from microsoft.teams.auth import (
    BotTokenValidator,
    TokenAuthenticationError,
    TokenClaimsError,
    TokenFormatError,
    TokenInfrastructureError,
)
from microsoft.teams.common.logging import ConsoleLogger


class HttpPlugin:
    """
    Basic HTTP plugin that provides a FastAPI server for Teams activities.
    """

    def __init__(
        self,
        app_id: Optional[str],
        logger: Optional[Logger] = None,
        activity_handler: Optional[Callable[..., Any]] = None,
    ):
        self.logger = logger or ConsoleLogger().create_logger("@teams/http-plugin")
        self._server: Optional[uvicorn.Server] = None
        self._port: Optional[int] = None

        # Storage for pending HTTP responses by activity ID
        self.pending: Dict[str, asyncio.Future[Any]] = {}

        # Activity handler for processing.
        # Once plugins work, this should be injected in.
        self.activity_handler = activity_handler

        # Bot token validator (only create if app_id is provided)
        self.token_validator = BotTokenValidator(app_id, self.logger) if app_id else None

        # Setup FastAPI app with lifespan
        @asynccontextmanager
        async def lifespan(_app: FastAPI) -> Any:
            # Startup
            self.logger.info(f"listening on port {self._port} 🚀")
            yield
            # Shutdown
            self.logger.info("Server shutting down")

        self.app = FastAPI(lifespan=lifespan)

        # Expose FastAPI routing methods (like TypeScript exposes Express methods)
        self.get = self.app.get
        self.post = self.app.post
        self.put = self.app.put
        self.patch = self.app.patch
        self.delete = self.app.delete
        self.route = self.app.route
        self.middleware = self.app.middleware

        # Setup routes and error handlers
        self._setup_routes()

    async def on_start(self, port: int) -> None:
        """Start the HTTP server."""
        self._port = port

        try:
            config = uvicorn.Config(app=self.app, host="0.0.0.0", port=port, log_level="info")
            self._server = uvicorn.Server(config)

            self.logger.info(f"Starting HTTP server on port {port}")

            # This will block, but the lifespan callback will signal startup completion
            if self._server:
                await self._server.serve()

        except OSError as error:
            # Handle port in use, permission errors, etc.
            self.logger.error(f"Server startup failed: {error}")
            raise
        except Exception as error:
            self.logger.error(f"Failed to start server: {error}")
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

    async def _process_activity(self, activity: Dict[str, Any], activity_id: str) -> None:
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
                await self.activity_handler(activity)
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

    def _extract_bearer_token(self, authorization: Optional[str]) -> Optional[str]:
        """Extract Bearer token from Authorization header."""
        if not authorization:
            return None

        if not authorization.startswith("Bearer "):
            return None

        return authorization.removeprefix("Bearer ")

    async def _authenticate_request(self, request: Request) -> tuple[Optional[str], Optional[str]]:
        """
        Extract and validate JWT token from request.

        Returns:
            Tuple of (token, service_url) if authentication succeeds

        Raises:
            HTTPException: If authentication fails
        """
        authorization = request.headers.get("authorization")
        token = self._extract_bearer_token(authorization)

        if not token:
            # Only allow missing tokens in local development
            if os.getenv("ENVIRONMENT") == "local":
                self.logger.debug("No authorization header in local development - allowing request")
                return None, None
            else:
                self.logger.warning("Unauthorized request - missing or invalid authorization header")
                raise HTTPException(status_code=401, detail="unauthorized")

        # Validate JWT token following Bot Framework protocol
        if self.token_validator:
            # Parse body to get service URL for validation
            body = await request.json()
            service_url = body.get("serviceUrl")

            try:
                await self.token_validator.validate_token(token, service_url)
                self.logger.debug("JWT token validation successful")
                return token, service_url
            except (TokenFormatError, TokenClaimsError, TokenAuthenticationError, TokenInfrastructureError) as e:
                self.logger.warning(f"JWT token validation failed: {e}")
                raise HTTPException(status_code=401, detail="unauthorized") from e
            except Exception as e:
                self.logger.error(f"Unexpected error during token validation: {e}")
                raise HTTPException(status_code=500, detail="internal server error") from e
        else:
            # No validator available (no app_id provided) - basic presence check only
            self.logger.warning("No token validator available - only checking token presence")
            return token, None

    async def _handle_activity_request(self, request: Request) -> Any:
        """
        Process the activity request and coordinate response.

        Args:
            request: The FastAPI request object
            token: The validated JWT token (if any)

        Returns:
            The activity processing result
        """
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
                asyncio.create_task(self._process_activity(body, activity_id))
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

        @self.app.post("/api/messages")  # type: ignore[misc]
        async def on_activity(request: Request) -> Any:
            """Handle incoming Teams activity."""
            # Authenticate request and extract token
            _token, _service_url = await self._authenticate_request(request)

            # Process the activity
            return await self._handle_activity_request(request)

        @self.app.get("/")  # type: ignore[misc]
        async def health_check() -> Dict[str, Any]:
            """Basic health check endpoint."""
            return {"status": "healthy", "port": self._port}
