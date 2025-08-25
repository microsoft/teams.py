"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import importlib.metadata
import os
from contextlib import asynccontextmanager
from datetime import datetime
from logging import Logger
from typing import Annotated, Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.routing import APIRouter
from fastapi.staticfiles import StaticFiles
from microsoft.teams.api import Activity, ActivityParams, ConversationReference, SentActivity, TokenProtocol
from microsoft.teams.apps import (
    ActivityEvent,
    DependencyMetadata,
    ErrorEvent,
    EventMetadata,
    HttpPlugin,
    LoggerDependencyOptions,
    Plugin,
    PluginActivityEvent,
    PluginActivityResponseEvent,
    PluginActivitySentEvent,
    PluginErrorEvent,
    PluginStartEvent,
    Sender,
)

from .event import DevToolsActivityEvent, DevToolsActivityReceivedEvent, DevToolsActivitySentEvent
from .page import Page
from .routes import RouteContext, get_router

version = importlib.metadata.version("microsoft-teams-devtools")


@Plugin(
    name="devtools",
    version=version,
    description="set of tools to make development of Teams apps faster and simpler",
)
class DevToolsPlugin(Sender):
    logger: Annotated[Logger, LoggerDependencyOptions()]
    id: Annotated[Optional[TokenProtocol], DependencyMetadata(optional=True)]
    name: Annotated[Optional[TokenProtocol], DependencyMetadata(optional=True)]
    http_plugin: Annotated[HttpPlugin, DependencyMetadata()]

    on_error_event: Annotated[Callable[[ErrorEvent], None], EventMetadata(name="error")]
    on_activity_event: Annotated[Callable[[ActivityEvent], None], EventMetadata(name="activity")]

    def __init__(self):
        super().__init__()
        self._server: Optional[uvicorn.Server] = None
        self._port: Optional[int] = None
        self._on_ready_callback: Optional[Callable[[], Awaitable[None]]] = None
        self._on_stopped_callback: Optional[Callable[[], Awaitable[None]]] = None

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
        self.sockets: Dict[str, WebSocket] = {}

        # Storage for pending HTTP responses by activity ID
        self.pending: Dict[str, asyncio.Future[Any]] = {}
        self.pages: List[Page] = []

        @self.app.websocket("/devtools/sockets")
        async def websocket_endpoint(websocket: WebSocket):  # type: ignore
            self.logger.info(f"WebSocket connection initiated with scope type: {websocket.scope['type']}")
            await self.on_socket_connection(websocket)

        dist = os.path.join(os.path.dirname(__file__), "web")
        self.app.mount("/devtools", StaticFiles(directory=dist, html=True), name="web")

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
        self.logger.warning("⚠️ Devtools is not secure and should not be used in production environments ⚠️")

    async def on_start(self, event: PluginStartEvent) -> None:
        self._port = event.port + 1

        try:
            router = APIRouter()

            async def process(token: TokenProtocol, activity: Activity):
                response_future = asyncio.get_event_loop().create_future()
                self.pending[activity.id] = response_future
                try:
                    result = self.on_activity_event(
                        ActivityEvent(token=token, activity=activity, sender=self.http_plugin)
                    )
                    # If the handler is a coroutine, schedule it
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as error:
                    response_future.set_exception(error)
                finally:
                    result = await response_future
                    if activity.id in self.pending:
                        del self.pending[activity.id]
                return result

            router.include_router(get_router(RouteContext(port=self._port, log=self.logger, process=process)))
            self.app.include_router(router)

            config = uvicorn.Config(app=self.app, host="0.0.0.0", port=self._port, log_level="info")
            self._server = uvicorn.Server(config)

            self.logger.info(f"available at http://localhost:{self._port}/devtools")

            # The lifespan handler will call the callback when the server is ready
            await self._server.serve()

        except OSError as error:
            # Handle port in use, permission errors, etc.
            await self.on_error(PluginErrorEvent(error=error))
            self.logger.error("Server startup failed: %s", error)
            raise
        except Exception as error:
            await self.on_error(PluginErrorEvent(error=error))
            self.logger.error("Failed to start server: %s", error)
            raise

    async def on_socket_connection(self, websocket: WebSocket):
        """Handle WebSocket connections."""
        await websocket.accept()
        socket_id = str(uuid4())
        self.sockets[socket_id] = websocket

        try:
            await websocket.send_json(
                {
                    "id": str(uuid4()),
                    "type": "metadata",
                    "body": {
                        "id": self.id.__str__(),
                        "name": self.name.__str__(),
                        "pages": self.pages,
                    },
                    "sent_at": datetime.now().isoformat(),
                }
            )

            # Event driven handling of incoming messages
            while True:
                try:
                    data = await websocket.receive_text()
                    self.logger.info(f"Received WebSocket message: {data}")
                except WebSocketDisconnect:
                    self.logger.info(f"WebSocket {socket_id} disconnected")
                    break
        finally:
            del self.sockets[socket_id]

    async def on_activity(self, event: PluginActivityEvent):
        """Handle incoming activities."""
        self.logger.debug("Activity received in on_activity")

        activity = DevToolsActivityReceivedEvent(
            id=str(uuid4()),
            type="activity.received",
            chat=event.activity.conversation,
            body=event.activity,
            sent_at=datetime.now(),
        )

        await self.emit_activity_to_sockets(activity)

    async def on_activity_sent(self, event: PluginActivitySentEvent):
        """Handle sent activities."""
        self.logger.debug(f"Activity sent: {event.activity}")

        activity = DevToolsActivitySentEvent(
            id=str(uuid4()),
            type="activity.sent",
            chat=event.conversation_ref.conversation,
            body=event.activity,
            sent_at=datetime.now(),
        )

        await self.emit_activity_to_sockets(activity)

    async def on_activity_response(self, event: PluginActivityResponseEvent):
        promise = self.pending.get(event.activity.id, None)
        if promise is not None:
            promise.set_result(event.response)
            del self.pending[event.activity.id]

    async def send(self, activity: ActivityParams, ref: ConversationReference) -> SentActivity:
        return await self.http_plugin.send(activity, ref)

    async def emit_activity_to_sockets(self, event: DevToolsActivityEvent):
        for socket_id, websocket in self.sockets.items():
            try:
                data = event.model_dump()
                # Convert datetime to ISO format for JSON serialization
                if isinstance(data.get("sentAt"), datetime):
                    data["sentAt"] = data["sentAt"].isoformat()
                await websocket.send_json(data)
            except WebSocketDisconnect:
                self.logger.info(f"WebSocket {socket_id} disconnected")
                del self.sockets[socket_id]

    def add_page(self, page: Page) -> "DevToolsPlugin":
        """Add a custom page to the DevTools."""
        self.pages.append(page)
        return self
