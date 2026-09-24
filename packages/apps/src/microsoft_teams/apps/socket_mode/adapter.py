"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# The public face of Socket Mode: an ``HttpServerAdapter`` that dials out instead of
# listening, so enabling it swaps the transport without touching the activity pipeline.
#
# Everything below the transport is owned by the rest of this package; this module is
# only the seam between it and the App -- envelope in, activity pipeline, reply frame out.

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Literal, Optional, Sequence, Union

from microsoft_teams.api import InvokeResponse, TokenProtocol
from microsoft_teams.api.auth.caller import CallerType
from microsoft_teams.common.events import EventEmitter

from ..events import ActivityEvent, CoreActivity
from ..http.adapter import HttpMethod, HttpRouteHandler
from .envelope import build_reply_frame, is_invoke_envelope, read_envelope_activity
from .transport import (
    DEFAULT_GEOS,
    DEFAULT_SOCKET_MODE_NEGOTIATE_BASE_URL,
    SocketModeTransport,
    SocketModeTransportOptions,
    build_negotiate_url,
)
from .types import (
    SOCKET_MODE_PROTOCOL_VERSION,
    ConnectionFactory,
    ReplyFrame,
    SocketActivityEnvelope,
    SocketModeCallbacks,
    SocketModeStatus,
    SocketReadyFrame,
)

logger = logging.getLogger(__name__)

SocketModeEventType = Literal["ready", "disconnected", "reconnected"]
"""Name of a lifecycle event emitted by :attr:`SocketModeAdapter.events`."""


@dataclass(frozen=True)
class SocketModeReadyEvent:
    """A geo's socket connected and the service confirmed readiness."""

    geo: str
    frame: SocketReadyFrame


@dataclass(frozen=True)
class SocketModeDisconnectedEvent:
    """
    A geo's socket dropped unexpectedly and a reconnect may be in progress.

    Not emitted for a planned credential rotation, which renegotiates without a visible drop.
    """

    geo: str
    error: Optional[Exception] = None


@dataclass(frozen=True)
class SocketModeReconnectedEvent:
    """A geo's socket recovered from an unexpected drop."""

    geo: str


@dataclass(frozen=True)
class SocketModeOptions:
    """
    Public tuning for Socket Mode. Durations are in **seconds**.
    """

    negotiate_base_url: str = DEFAULT_SOCKET_MODE_NEGOTIATE_BASE_URL
    """Service host used to negotiate the connection."""

    geos: Sequence[str] = DEFAULT_GEOS
    """
    Geographies to connect, one independent socket each. Every one must connect for
    ``start()`` to succeed, after which each is supervised on its own.
    """

    readiness_timeout: float = 30.0
    """How long to wait for the service's readiness frame after the socket opens."""

    startup_timeout: float = 30.0
    """Total budget for the initial connect, retried with backoff until it is spent."""

    reconnect_delays: Optional[Sequence[float]] = None
    """Explicit backoff schedule; the last value repeats. Defaults to capped exponential with jitter."""

    keep_alive_interval: float = 15.0
    """Ping cadence. Keep comfortably below ``server_timeout``."""

    server_timeout: float = 30.0
    """How long without an inbound message before the connection is considered lost."""

    def to_transport_options(self) -> SocketModeTransportOptions:
        return SocketModeTransportOptions(
            negotiate_base_url=self.negotiate_base_url,
            geos=tuple(self.geos),
            readiness_timeout=self.readiness_timeout,
            startup_timeout=self.startup_timeout,
            reconnect_delays=self.reconnect_delays,
            keep_alive_interval=self.keep_alive_interval,
            server_timeout=self.server_timeout,
        )


@dataclass(frozen=True)
class _SocketModeToken:
    """
    The token the activity pipeline expects, for an activity that arrived without one.

    A Socket Mode activity is authenticated by the connection it came in on -- the service
    only opens that socket after the negotiate call presented the bot's credentials -- so
    there is no per-activity bearer token to validate. This carries the identity the
    pipeline needs and nothing more: it is never a credential, never leaves the process,
    and deliberately stringifies to empty so it cannot be mistaken for one and forwarded.
    """

    app_id: str
    service_url: str
    app_display_name: Optional[str] = None
    tenant_id: Optional[str] = None
    from_: CallerType = "azure"
    from_id: str = ""
    expiration: Optional[int] = None

    def is_expired(self, buffer_ms: int = 5 * 60 * 1000) -> bool:
        return False

    def __str__(self) -> str:
        return ""


class SocketModeAdapter:
    """
    Receives activities over an outbound WebSocket instead of an inbound HTTPS endpoint.

    Implements :class:`~microsoft_teams.apps.http.adapter.HttpServerAdapter` so the App can
    treat it as any other server: ``start``/``stop`` drive the sockets, and the route
    registration the App performs at startup is accepted and ignored because a socket
    serves only the messaging endpoint.
    """

    def __init__(
        self,
        options: Optional[SocketModeOptions] = None,
        *,
        process_activity: Callable[[ActivityEvent], Awaitable[InvokeResponse[Any]]],
        get_app_token: Callable[[], Awaitable[Optional[TokenProtocol]]],
        messaging_endpoint: str = "/api/messages",
        client_id: Optional[str] = None,
        on_error: Optional[Callable[[Exception], Union[None, Awaitable[None]]]] = None,
        connection_factory: Optional[ConnectionFactory] = None,
    ):
        self.options = options or SocketModeOptions()
        self._process_activity = process_activity
        self._get_app_token = get_app_token
        self._messaging_endpoint = messaging_endpoint
        self._client_id = client_id
        self._on_error = on_error
        self.events: EventEmitter[SocketModeEventType] = EventEmitter[SocketModeEventType]()

        self._transport = SocketModeTransport(
            self.options.to_transport_options(),
            get_bot_token=self._acquire_bot_token,
            on_activity=self._handle_envelope,
            callbacks=SocketModeCallbacks(
                on_ready=lambda geo, frame: self.events.emit("ready", SocketModeReadyEvent(geo=geo, frame=frame)),
                on_disconnected=lambda geo, error: self.events.emit(
                    "disconnected", SocketModeDisconnectedEvent(geo=geo, error=error)
                ),
                on_reconnected=lambda geo: self.events.emit("reconnected", SocketModeReconnectedEvent(geo=geo)),
            ),
            connection_factory=connection_factory,
            logger=logger,
        )

    @property
    def status(self) -> SocketModeStatus:
        """Aggregate status across geos: ready only when all are, disconnected when any has dropped."""
        return self._transport.status

    @property
    def geo_statuses(self) -> tuple[tuple[str, SocketModeStatus], ...]:
        """Per-geo status snapshot, for diagnostics."""
        return self._transport.geo_statuses

    @property
    def geo_list(self) -> tuple[str, ...]:
        """The geos this adapter connects to."""
        return tuple(self.options.geos)

    @property
    def negotiate_url(self) -> str:
        """Resolved negotiate URL for the first geo. Each geo dials its own."""
        geos = self.geo_list
        return build_negotiate_url(self.options.negotiate_base_url, geos[0] if geos else "")

    def register_route(self, method: HttpMethod, path: str, handler: HttpRouteHandler) -> None:
        """
        Accept the App's messaging route as a no-op -- inbound frames are dispatched
        internally, so nothing needs to be mounted. Any other route is warned about
        because the HTTP-only feature behind it will not work over a socket.
        """
        if method == "POST" and path == self._messaging_endpoint:
            return
        logger.warning(
            "socket-mode: ignoring %s %s - Socket Mode serves only the messaging endpoint, "
            "so HTTP-only features (app.function(), OAuth redirect routes) are unavailable.",
            method,
            path,
        )

    def serve_static(self, path: str, directory: str) -> None:
        logger.warning(
            "socket-mode: ignoring serve_static(%s) - Socket Mode has no HTTP listener to serve files from.",
            path,
        )

    async def start(self, port: int = 0) -> None:
        """
        Open one socket per geo, then serve until stopped.

        ``port`` is part of the server contract and ignored: Socket Mode dials out rather
        than listening. A geo that cannot connect within the startup budget fails the
        whole start, leaving nothing running.

        Like the HTTP adapters this replaces, it does not return while serving -- the
        App awaits it for the lifetime of the process. Connecting is not the end of the
        work, so returning once the sockets were up would let ``App.start()`` fall
        through and tear down the event loop that the sockets are running on.
        """
        await self._transport.start()
        await self._transport.stop_event.wait()

    async def stop(self) -> None:
        await self._transport.stop()

    async def _acquire_bot_token(self) -> str:
        token = await self._get_app_token()
        if token is None:
            raise RuntimeError(
                "Socket Mode could not acquire a Bot Framework app token. "
                "Check that the app credentials (client_id / client_secret / tenant_id) are configured."
            )
        return str(token)

    async def _handle_envelope(self, envelope: SocketActivityEnvelope) -> Optional[ReplyFrame]:
        """
        Run one inbound envelope through the App's pipeline and build the frame to reply with.

        An invoke returns the handler's status and body; a one-way activity is acknowledged
        once the pipeline has run.
        """
        declared = envelope.protocol_version
        if declared is not None and declared > SOCKET_MODE_PROTOCOL_VERSION:
            # Refused before dispatch, not after: a future major version may change what a
            # reply means, so running the handler and answering in v1 could be misread as
            # success. Older or absent versions are treated as current.
            logger.warning(
                "socket-mode: rejecting envelope with unsupported protocol version %s (supported %s)",
                declared,
                SOCKET_MODE_PROTOCOL_VERSION,
            )
            return build_reply_frame(
                envelope,
                bot_key=self._client_id,
                status=400,
                body={"error": f"unsupported protocolVersion {declared}"},
            )

        activity = read_envelope_activity(envelope)
        if activity is None:
            logger.warning("socket-mode: inbound envelope carried no activity; dropping")
            return None

        invoke = is_invoke_envelope(envelope)
        try:
            core_activity = CoreActivity.model_validate(dict(activity))
            response = await self._process_activity(
                ActivityEvent(
                    body=core_activity,
                    token=_SocketModeToken(
                        app_id=self._client_id or "",
                        service_url=str(activity.get("serviceUrl") or ""),
                    ),
                )
            )
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.exception("socket-mode: failed to process an inbound activity")
            await self._report_error(error)
            return build_reply_frame(
                envelope,
                bot_key=self._client_id,
                status=500,
                body={"error": "bot handler error"} if invoke else None,
            )

        return build_reply_frame(
            envelope,
            bot_key=self._client_id,
            status=response.status,
            body=response.body if invoke else None,
        )

    async def _report_error(self, error: Exception) -> None:
        """Surface a handler failure to the App, never letting the hook itself break the socket."""
        if self._on_error is None:
            return
        try:
            result = self._on_error(error)
            if isinstance(result, Awaitable):
                await result
        except Exception:
            logger.warning("socket-mode: on_error hook raised; ignoring", exc_info=True)
