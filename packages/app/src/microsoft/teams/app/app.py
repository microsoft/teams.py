"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, overload

F = TypeVar("F", bound=Callable[..., Any])

from microsoft.teams.api import Activity, ApiClient, ClientCredentials, Credentials, JsonWebToken, TokenProtocol
from microsoft.teams.common.events import EventEmitter
from microsoft.teams.common.http import Client
from microsoft.teams.common.logging import ConsoleLogger
from microsoft.teams.common.storage import LocalStorage

from .events import (
    ActivityEvent,
    ErrorEvent,
    EventType,
    StartEvent,
    StopEvent,
    TokenEvent,
    get_event_type_from_signature,
    is_registered_event,
)
from .http_plugin import HttpPlugin
from .options import AppOptions
from .plugin import PluginProtocol


@dataclass
class AppTokens:
    """Application tokens for API access."""

    bot: Optional[TokenProtocol] = None
    graph: Optional[TokenProtocol] = None


class App:
    """
    The main Teams application orchestrator.

    Manages plugins, tokens, and application lifecycle for Microsoft Teams apps.
    """

    def __init__(self, options: Optional[AppOptions] = None):
        self.options = options or AppOptions()

        # Setup logging and storage
        self.log = self.options.logger or ConsoleLogger().create_logger("@teams/app")
        self.storage = self.options.storage or LocalStorage()

        # Initialize HTTP client
        self.http_client = Client()

        # Initialize event system
        self._events = EventEmitter()

        # Initialize tokens and credentials
        self._tokens = AppTokens()
        self.credentials = self._init_credentials()

        # Initialize API client with hardcoded service URL (matching TypeScript pattern)
        self.api = ApiClient("https://smba.trafficmanager.net/teams", self.http_client)

        # TODO: Initialize graph client when available
        # self.graph = GraphClient(self.http_client)

        # Activity handler
        self.activity_handler = self.options.activity_handler

        # Initialize plugins (matching TypeScript pattern)
        plugins: List[PluginProtocol] = list(self.options.plugins or [])

        # Find or create HTTP plugin (matching TypeScript behavior)
        http_plugin = None
        for i, plugin in enumerate(plugins):
            if isinstance(plugin, HttpPlugin):
                http_plugin = plugin
                # Remove HTTP plugin from its current position
                plugins.pop(i)
                break

        if not http_plugin:
            # Get app_id from credentials for JWT validation
            app_id = None
            if self.credentials and hasattr(self.credentials, "client_id"):
                app_id = self.credentials.client_id

            http_plugin = HttpPlugin(app_id, self.log, self.handle_activity)

        # Always put HTTP plugin LAST since it blocks
        plugins.append(http_plugin)

        self.plugins = plugins
        self.http = http_plugin

        # Wire up activity handler to HTTP plugin
        # TODO: When plugin architecture is done, remove this manual wiring
        self.http.activity_handler = self.handle_activity

        # App state
        self._port: Optional[int] = None
        self._running = False

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
            # Refresh tokens
            await self._refresh_tokens(force=True)

            # Mark as running before starting plugins
            self._running = True

            # Start plugins (HTTP plugin will block here, keeping server running)
            self.log.info("Teams app started successfully")

            # Emit start event
            self._events.emit("start", StartEvent(port=self._port))

            for plugin in self.plugins:
                await plugin.on_start(self._port)

        except Exception as error:
            self._running = False  # Reset on failure
            self.log.error(f"Failed to start app: {error}")

            # Emit error event
            self._events.emit("error", ErrorEvent(error, context={"method": "start", "port": self._port}))
            raise

    async def stop(self) -> None:
        """Stop the Teams application."""
        if not self._running:
            return

        try:
            # Stop plugins in reverse order
            for plugin in reversed(self.plugins):
                await plugin.on_stop()

            self._running = False
            self.log.info("Teams app stopped")

            # Emit stop event
            self._events.emit("stop", StopEvent())

        except Exception as error:
            self.log.error(f"Failed to stop app: {error}")

            # Emit error event
            self._events.emit("error", ErrorEvent(error, context={"method": "stop"}))
            raise

    def _init_credentials(self) -> Optional[Credentials]:
        """Initialize authentication credentials from options and environment."""
        client_id = self.options.client_id or os.getenv("CLIENT_ID")
        client_secret = self.options.client_secret or os.getenv("CLIENT_SECRET")
        tenant_id = self.options.tenant_id or os.getenv("TENANT_ID")

        if client_id and client_secret:
            return ClientCredentials(client_id=client_id, client_secret=client_secret, tenant_id=tenant_id)

        return None

    async def _refresh_tokens(self, force: bool = False) -> None:
        """Refresh bot and graph tokens."""
        await asyncio.gather(self._refresh_bot_token(force), self._refresh_graph_token(force), return_exceptions=True)

    async def _refresh_bot_token(self, force: bool = False) -> None:
        """Refresh the bot authentication token."""
        if not self.credentials:
            return

        if not force and self._tokens.bot and not self._tokens.bot.is_expired():
            return

        if self._tokens.bot:
            self.log.debug("Refreshing bot token")

        try:
            token_response = await self.api.bots.token.get(self.credentials)
            self._tokens.bot = JsonWebToken(token_response.access_token)
            self.log.debug("Bot token refreshed successfully")

            # Emit token event (without actual token for security)
            self._events.emit("token", TokenEvent(token_type="bot"))
        except Exception as error:
            self.log.error(f"Failed to refresh bot token: {error}")

            # Emit error event
            self._events.emit("error", ErrorEvent(error, context={"method": "_refresh_bot_token"}))
            raise

    async def _refresh_graph_token(self, force: bool = False) -> None:
        """Refresh the Graph API token."""
        if not self.credentials:
            return

        if not force and self._tokens.graph and not self._tokens.graph.is_expired():
            return

        if self._tokens.graph:
            self.log.debug("Refreshing graph token")

        try:
            # TODO: Implement graph token refresh when graph client is available
            # token_response = await self.api.bots.token.get_graph(self.credentials)
            # self._tokens.graph = JsonWebToken(token_response.access_token)
            self.log.debug("Graph token refresh not yet implemented")

            # When implemented, emit token event:
            # self._events.emit("token", TokenEvent(token_type="graph"))
        except Exception as error:
            self.log.error(f"Failed to refresh graph token: {error}")

            # Emit error event
            self._events.emit("error", ErrorEvent(error, context={"method": "_refresh_graph_token"}))
            raise

    async def handle_activity(self, activity: Activity) -> Dict[str, Any]:
        """
        Dummy activity handler for testing the event-driven pattern.

        Args:
            activity: The Teams activity data
            token: The authorization token
            http_plugin: The HTTP plugin instance

        Returns:
            Response data to send back
        """
        activity_type = activity.type
        activity_id = activity.id or ""

        self.log.info(f"Processing activity {activity_id} of type {activity_type}")

        try:
            # Emit activity event
            self._events.emit("activity", ActivityEvent(activity))

            response = None
            if self.activity_handler:
                response = await self.activity_handler(activity)

            # Log completion and return response
            self.log.info(f"Completed processing activity {activity_id}")
            self.http.on_activity_response(activity_id, response)

            return {
                "status": "processed",
                "message": f"Successfully handled {activity_type} activity",
                "activityId": activity_id,
            }
        except Exception as error:
            self.log.error(f"Failed to process activity {activity_id}: {error}")

            # Emit error event
            self._events.emit(
                "error",
                ErrorEvent(
                    error,
                    context={"method": "handle_activity", "activity_id": activity_id, "activity_type": activity_type},
                ),
            )
            raise

    @overload
    def event(self, func: F) -> F:
        """Register event handler with auto-detected type from function signature."""
        ...

    @overload
    def event(self, event_type: Union[EventType, str]) -> Callable[[F], F]:
        """Register event handler with explicit event type."""
        ...

    @overload
    def event(self, func: None = None, *, event_type: Union[EventType, str]) -> Callable[[F], F]:
        """Register event handler with explicit event type (keyword)."""
        ...

    def event(
        self,
        func_or_event_type: Union[F, EventType, str, None] = None,
        *,
        event_type: Optional[Union[EventType, str]] = None,
    ) -> Union[F, Callable[[F], F]]:
        """
        Decorator to register event handlers with automatic type inference.

        Can be used in multiple ways:
        - @app.event (auto-detect from type hints)
        - @app.event("activity")
        - @app.event(event_type="error")

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
            # Determine event type
            detected_type = None

            if event_type:
                # Explicit event_type parameter
                detected_type = event_type
            elif isinstance(func_or_event_type, str):
                # String passed as first argument
                detected_type = func_or_event_type
            else:
                # Try to auto-detect from function signature
                detected_type = get_event_type_from_signature(func)

            if not detected_type:
                raise ValueError(
                    f"Could not determine event type for {func.__name__}. "
                    "Either provide an explicit event_type or use a typed parameter."
                )

            # Validate that the event type is registered
            if not is_registered_event(detected_type):
                raise ValueError(
                    f"Event type '{detected_type}' is not registered. "
                    f"Use register_event_type() to register custom events."
                )

            # Register the handler with the app's event emitter
            self._events.on(detected_type, func)
            return func

        # Handle different calling patterns
        if callable(func_or_event_type) and not isinstance(func_or_event_type, str):
            # Called as @app.event (without parentheses)
            return decorator(func_or_event_type)
        else:
            # Called as @app.event() or @app.event("type")
            return decorator
