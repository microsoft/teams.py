"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Fans Socket Mode out across geographies and owns the start/stop lifecycle.
#
# ``start()`` is all-or-nothing: every configured geo must reach ``SocketReady`` or the
# whole transport is torn down and the error raised, so a partially connected transport
# is never reported as running. Once up, each geo is supervised independently and one
# geo dropping has no effect on the others.
#
# This module also owns the policy the supervisors consult -- backoff, throttling, and
# refresh timing -- keeping those decisions in one place.

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Awaitable, Callable, Optional, Sequence
from urllib.parse import quote

import httpx

from .connection import SignalRSocketConnection, SocketConnectionContext
from .geo_socket import GeoSocket
from .negotiate import NegotiateError
from .types import (
    ConnectionFactory,
    ReplyFrame,
    SocketActivityEnvelope,
    SocketConnection,
    SocketConnectionHandlers,
    SocketModeCallbacks,
    SocketModeStatus,
    SocketReadyFrame,
    WebSocketFactory,
)

DEFAULT_SOCKET_MODE_NEGOTIATE_BASE_URL = "https://botapi.skype.com"
"""Default service host used to negotiate the connection."""

SOCKET_MODE_NEGOTIATE_PATH = "/v3/websockets/connect"
"""Negotiate route appended to the base URL: ``POST {base}/{geo}/v3/websockets/connect``."""

DEFAULT_GEOS = ("amer", "emea", "apac")
"""Geographies connected by default, one independent socket each."""

TOKEN_REFRESH_MARGIN = 60.0
"""
Seconds before the negotiate token expires at which the connection is proactively
replaced, so a refresh happens on a healthy socket rather than after an auth drop.
Deliberately not an option: it is service-coupled tuning, not a user knob.
"""

RECONNECT_INITIAL_DELAY = 1.0
"""Base of the exponential reconnect backoff, in seconds."""

RECONNECT_MAX_DELAY = 15.0
"""Ceiling the exponential reconnect backoff is capped at, in seconds."""


@dataclass(frozen=True)
class SocketModeTransportOptions:
    """
    Tuning for :class:`SocketModeTransport`. All durations are in **seconds**
    (the TypeScript SDK uses milliseconds with an ``Ms`` suffix).
    """

    negotiate_base_url: str = DEFAULT_SOCKET_MODE_NEGOTIATE_BASE_URL
    geos: Sequence[str] = DEFAULT_GEOS
    """
    Every listed geo must connect for ``start()`` to succeed; each is then supervised
    independently, so one geo dropping never affects the others. Pass ``("",)`` to
    connect to the base URL with no geo segment.
    """

    readiness_timeout: float = 30.0
    """How long to wait for ``SocketReady`` after the socket opens."""

    startup_timeout: float = 30.0
    """
    Total budget for the *initial* connect. Retried with the same backoff as reconnect
    until this is exhausted, after which ``start()`` raises. ``0`` fails on the first
    attempt. Once connected, the supervisor retries indefinitely until ``stop()``.
    """

    reconnect_delays: Optional[Sequence[float]] = None
    """
    Explicit reconnect backoff schedule. Values are used in order and the last one
    repeats. When omitted, a capped exponential schedule with jitter is used.
    """

    keep_alive_interval: float = 15.0
    """Ping cadence, sent unconditionally. Keep comfortably below ``server_timeout``."""

    server_timeout: float = 30.0
    """
    How long without an **inbound** message before the connection is considered lost.
    Only inbound frames reset it, so too low a value causes reconnect churn when idle.
    """


class SocketModeTransport:
    """Owns one socket per geography and the policy that keeps them connected."""

    def __init__(
        self,
        options: SocketModeTransportOptions,
        *,
        get_bot_token: Callable[[], Awaitable[str]],
        on_activity: Callable[[SocketActivityEnvelope], Awaitable[Optional[ReplyFrame]]],
        callbacks: Optional[SocketModeCallbacks] = None,
        connection_factory: Optional[ConnectionFactory] = None,
        http_client: Optional[httpx.AsyncClient] = None,
        websocket_factory: Optional[WebSocketFactory] = None,
        logger: Optional[logging.Logger] = None,
    ):
        self._options = options
        self._get_bot_token = get_bot_token
        self._on_activity = on_activity
        self._callbacks = callbacks or SocketModeCallbacks()
        self._connection_factory = connection_factory
        self._http_client = http_client
        self._websocket_factory = websocket_factory
        self._logger = logger or logging.getLogger(__name__)
        self._lifecycle = SocketModeStatus.IDLE
        self._stop_event = asyncio.Event()
        self._stop_event.set()
        self._geos: list[GeoSocket] = []
        self._lifecycle_lock = asyncio.Lock()

    @property
    def status(self) -> SocketModeStatus:
        """
        Aggregate status across geos: ready only when all are ready, disconnected when any
        has dropped, otherwise connecting.
        """
        if self._lifecycle in {SocketModeStatus.IDLE, SocketModeStatus.STOPPED}:
            return self._lifecycle
        states = [geo.status for geo in self._geos]
        if states and all(state == SocketModeStatus.READY for state in states):
            return SocketModeStatus.READY
        if any(state == SocketModeStatus.DISCONNECTED for state in states):
            return SocketModeStatus.DISCONNECTED
        return SocketModeStatus.CONNECTING

    @property
    def geo_statuses(self) -> tuple[tuple[str, SocketModeStatus], ...]:
        return tuple((geo.geo, geo.status) for geo in self._geos)

    @property
    def accepting(self) -> bool:
        """Whether work should still be started or dispatched. False as soon as stop begins."""
        return (
            self._lifecycle in {SocketModeStatus.CONNECTING, SocketModeStatus.READY} and not self._stop_event.is_set()
        )

    @property
    def stop_event(self) -> asyncio.Event:
        return self._stop_event

    @property
    def startup_timeout(self) -> float:
        return self._options.startup_timeout

    @property
    def token_refresh_margin(self) -> float:
        return TOKEN_REFRESH_MARGIN

    async def start(self) -> None:
        """
        Connect every configured geo, or none of them.

        Validation happens before any socket is opened. If any geo fails, the rest are
        cancelled and stopped before the error is raised, so a failed start leaves nothing
        running.
        """
        async with self._lifecycle_lock:
            if self._lifecycle == SocketModeStatus.READY:
                return
            if self._options.startup_timeout < 0:
                raise ValueError("Socket Mode startup_timeout must be non-negative")
            geos = tuple(self._options.geos)
            if not geos:
                raise ValueError("Socket Mode geos must contain at least one entry")
            if len(set(geos)) != len(geos):
                raise ValueError("Socket Mode geos must not contain duplicates")

            self._stop_event = asyncio.Event()
            self._lifecycle = SocketModeStatus.CONNECTING
            self._geos = [
                GeoSocket(self, geo, _build_negotiate_url(self._options.negotiate_base_url, geo), self._logger)
                for geo in geos
            ]
            tasks = [
                asyncio.create_task(geo.start_initial(), name=f"teams-socket-mode-start-{geo or 'default'}")
                for geo in self._geos
            ]
            try:
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
                error = next(
                    (task.exception() for task in done if not task.cancelled() and task.exception() is not None),
                    None,
                )
                if error is not None:
                    self._stop_event.set()
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await asyncio.gather(*(geo.stop() for geo in self._geos), return_exceptions=True)
                    self._lifecycle = SocketModeStatus.STOPPED
                    raise error
                await asyncio.gather(*pending)
            except asyncio.CancelledError:
                self._stop_event.set()
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.gather(*(geo.stop() for geo in self._geos), return_exceptions=True)
                self._lifecycle = SocketModeStatus.STOPPED
                raise
            self._lifecycle = SocketModeStatus.READY
            for geo in self._geos:
                geo.supervise_in_background()

    async def stop(self) -> None:
        """
        Stop every geo. Idempotent, and serialized against ``start()`` so the two cannot
        interleave.
        """
        async with self._lifecycle_lock:
            if self._lifecycle == SocketModeStatus.STOPPED:
                return
            self._stop_event.set()
            await asyncio.gather(*(geo.stop() for geo in self._geos), return_exceptions=True)
            self._lifecycle = SocketModeStatus.STOPPED

    def create_connection(
        self,
        negotiate_url: str,
        handlers: SocketConnectionHandlers,
    ) -> SocketConnection:
        if self._connection_factory is not None:
            return self._connection_factory(negotiate_url, handlers)
        return SignalRSocketConnection(
            SocketConnectionContext(
                negotiate_url=negotiate_url,
                get_bot_token=self._get_bot_token,
                readiness_timeout=self._options.readiness_timeout,
                keep_alive_interval=self._options.keep_alive_interval,
                server_timeout=self._options.server_timeout,
            ),
            handlers,
            http_client=self._http_client,
            websocket_factory=self._websocket_factory,
        )

    def backoff_delay(self, attempt: int) -> float:
        """
        Delay before the next attempt: a configured schedule when given, otherwise
        exponential growth capped at :data:`RECONNECT_MAX_DELAY`.

        Jittered across the whole range so that geos, and separate bot instances, do not
        reconnect in lockstep after a service blip.
        """
        schedule = self._options.reconnect_delays
        if schedule:
            return max(0.0, schedule[min(attempt, len(schedule) - 1)])
        cap = min(RECONNECT_INITIAL_DELAY * (2**attempt), RECONNECT_MAX_DELAY)
        return random.uniform(0.0, cap)

    def retry_after_of(self, error: Optional[Exception]) -> Optional[float]:
        """The service's requested delay, which takes precedence over local backoff."""
        return error.retry_after if isinstance(error, NegotiateError) else None

    async def sleep(self, delay: float) -> bool:
        """Wait, returning ``False`` if stop was requested first so the caller can bail out."""
        if delay <= 0:
            await asyncio.sleep(0)
            return not self._stop_event.is_set()
        try:
            await asyncio.wait_for(self._stop_event.wait(), timeout=delay)
            return False
        except asyncio.TimeoutError:
            return True

    async def dispatch(
        self,
        geo_socket: GeoSocket,
        generation: int,
        envelope: SocketActivityEnvelope,
    ) -> Optional[ReplyFrame]:
        """Hand an activity to the application, unless its generation has been superseded."""
        if not geo_socket.can_dispatch(generation):
            return None
        return await self._on_activity(envelope)

    def geo_ready(self, geo: str, frame: SocketReadyFrame) -> None:
        callback = self._callbacks.on_ready
        if callback is not None:
            self._call_lifecycle(callback, geo, frame)

    def geo_disconnected(self, geo: str, error: Optional[Exception]) -> None:
        callback = self._callbacks.on_disconnected
        if callback is not None:
            self._call_lifecycle(callback, geo, error)

    def geo_reconnected(self, geo: str) -> None:
        callback = self._callbacks.on_reconnected
        if callback is not None:
            self._call_lifecycle(callback, geo)

    def _call_lifecycle(self, callback: Callable[..., None], *args: object) -> None:
        try:
            callback(*args)
        except Exception as error:
            self._logger.warning("Socket Mode lifecycle callback failed", exc_info=error)


def _build_negotiate_url(base_url: str, geo: str) -> str:
    base = base_url.rstrip("/")
    segment = geo.strip().strip("/")
    if segment:
        return f"{base}/{quote(segment, safe='')}{SOCKET_MODE_NEGOTIATE_PATH}"
    return f"{base}{SOCKET_MODE_NEGOTIATE_PATH}"
