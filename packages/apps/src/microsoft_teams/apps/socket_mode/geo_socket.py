"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Keeps one geography connected: initial connect within a startup budget, then
# supervision that reconnects with backoff for as long as the transport is accepting.
#
# Each connection attempt gets a monotonically increasing *generation*. Because a
# replaced connection's in-flight callbacks can still fire, generations are what make
# stale work identifiable: an activity is only dispatched when its generation is both
# the current one and the one that satisfied ``SocketReady``. A closed or superseded
# connection can therefore never deliver an activity or a reply.

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional, Protocol

from .types import (
    ReplyFrame,
    SocketActivityEnvelope,
    SocketConnection,
    SocketConnectionHandlers,
    SocketModeStatus,
    SocketReadyFrame,
)


class GeoSocketOwner(Protocol):
    """
    What a :class:`GeoSocket` needs from the transport that owns it.

    Expressed as a protocol so retry policy, dispatch, and lifecycle reporting stay in the
    transport while remaining substitutable in tests.
    """

    @property
    def accepting(self) -> bool: ...

    @property
    def stop_event(self) -> asyncio.Event: ...

    @property
    def startup_timeout(self) -> float: ...

    @property
    def token_refresh_margin(self) -> float: ...

    def create_connection(self, negotiate_url: str, handlers: SocketConnectionHandlers) -> SocketConnection: ...

    def backoff_delay(self, attempt: int) -> float: ...

    def retry_after_of(self, error: Optional[Exception]) -> Optional[float]: ...

    async def sleep(self, delay: float) -> bool: ...

    async def dispatch(
        self,
        geo_socket: "GeoSocket",
        generation: int,
        envelope: SocketActivityEnvelope,
    ) -> Optional[ReplyFrame]: ...

    def geo_ready(self, geo: str, frame: SocketReadyFrame) -> None: ...

    def geo_disconnected(self, geo: str, error: Optional[Exception]) -> None: ...

    def geo_reconnected(self, geo: str) -> None: ...


@dataclass(frozen=True)
class _CloseReason:
    """Why a connection ended: a planned swap (credential refresh) or an actual failure."""

    planned: bool
    error: Optional[Exception] = None


class GeoSocket:
    """One geography's connection and the supervision that keeps it alive."""

    def __init__(
        self,
        owner: GeoSocketOwner,
        geo: str,
        negotiate_url: str,
        logger: logging.Logger,
    ):
        self._owner = owner
        self.geo = geo
        self._negotiate_url = negotiate_url
        self._logger = logger
        self._generation = 0
        self._current_generation = 0
        self._ready_generation = -1
        self._connection: Optional[SocketConnection] = None
        self._closed: Optional[asyncio.Future[_CloseReason]] = None
        self._supervisor: Optional[asyncio.Task[None]] = None
        self._refresh: Optional[asyncio.Task[None]] = None
        self._status = SocketModeStatus.IDLE

    @property
    def status(self) -> SocketModeStatus:
        return self._status

    def can_dispatch(self, generation: int) -> bool:
        """
        Whether an activity from ``generation`` may still be handled.

        All three conditions matter: the transport must be accepting, the generation must
        be the newest, and it must be the one that reached ``SocketReady``. The last
        condition is what rejects activities that arrive after a close, since
        ``on_closed`` resets the ready generation.
        """
        return self._owner.accepting and generation == self._current_generation and generation == self._ready_generation

    async def start_initial(self) -> None:
        """
        Establish the first connection, retrying until the startup budget is spent.

        Raises the last error once the budget is exhausted, so a geo that never comes up
        fails ``start()`` rather than silently degrading.
        """
        self._status = SocketModeStatus.CONNECTING
        deadline = asyncio.get_running_loop().time() + self._owner.startup_timeout
        attempt = 0
        last_error: Optional[Exception] = None

        while self._owner.accepting:
            generation = self._next_generation()
            try:
                self._closed = await self._connect_cycle(generation)
                self._status = SocketModeStatus.READY
                return
            except asyncio.CancelledError:
                raise
            except Exception as error:
                last_error = error
                if not self._owner.accepting:
                    break
                delay = self._owner.retry_after_of(error)
                if delay is None:
                    delay = self._owner.backoff_delay(attempt)
                attempt += 1
                if self._owner.startup_timeout <= 0 or asyncio.get_running_loop().time() + delay >= deadline:
                    break
                self._logger.warning(
                    "socket-mode[%s]: initial connection failed; retrying in %.3fs",
                    self.geo,
                    delay,
                    exc_info=error,
                )
                if not await self._owner.sleep(delay):
                    break

        if last_error is not None:
            raise last_error
        raise ConnectionError(f"Socket Mode failed to establish the initial connection for geo '{self.geo}'")

    def supervise_in_background(self) -> None:
        """Start watching for close so the geo reconnects on its own. Idempotent."""
        if self._supervisor is None or self._supervisor.done():
            self._supervisor = asyncio.create_task(
                self._supervise(),
                name=f"teams-socket-mode-supervisor-{self.geo or 'default'}",
            )

    async def stop(self) -> None:
        """Tear down the refresh timer, connection, and supervisor, in that order."""
        self._cancel_refresh()
        connection = self._connection
        self._connection = None
        if connection is not None:
            try:
                await connection.stop()
            except Exception as error:
                self._logger.debug("socket-mode[%s]: connection stop failed", self.geo, exc_info=error)

        supervisor = self._supervisor
        self._supervisor = None
        if supervisor is not None and supervisor is not asyncio.current_task() and not supervisor.done():
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)
        self._ready_generation = -1
        self._status = SocketModeStatus.STOPPED

    def _next_generation(self) -> int:
        self._generation += 1
        self._current_generation = self._generation
        return self._generation

    async def _connect_cycle(self, generation: int) -> asyncio.Future[_CloseReason]:
        """
        Build and start one connection, returning the future that resolves when it closes.

        The handlers close over ``generation``, which is what lets a late callback from a
        superseded connection be recognised and ignored. A connection that starts without
        reaching ``SocketReady`` is treated as failed rather than usable.
        """
        loop = asyncio.get_running_loop()
        closed: asyncio.Future[_CloseReason] = loop.create_future()

        async def on_activity(envelope: SocketActivityEnvelope) -> Optional[ReplyFrame]:
            return await self._owner.dispatch(self, generation, envelope)

        def on_ready(frame: SocketReadyFrame) -> None:
            if generation != self._current_generation or not self._owner.accepting:
                return
            self._ready_generation = generation
            self._status = SocketModeStatus.READY
            self._owner.geo_ready(self.geo, frame)

        def on_closed(error: Optional[Exception]) -> None:
            if generation == self._current_generation:
                self._ready_generation = -1
            if not closed.done():
                closed.set_result(_CloseReason(planned=False, error=error))

        handlers = SocketConnectionHandlers(
            on_activity=on_activity,
            on_ready=on_ready,
            on_closed=on_closed,
        )
        connection = self._owner.create_connection(self._negotiate_url, handlers)
        self._connection = connection
        try:
            await connection.start(self._owner.stop_event)
        except BaseException:
            if self._connection is connection:
                self._connection = None
            try:
                await connection.stop()
            except Exception as error:
                self._logger.debug("socket-mode[%s]: failed connection cleanup", self.geo, exc_info=error)
            raise

        if self._ready_generation != generation:
            await connection.stop()
            raise ConnectionError("Socket Mode connection started without satisfying SocketReady")
        self._schedule_refresh(generation, connection.expires_in_seconds, closed)
        return closed

    async def _supervise(self) -> None:
        closed = self._closed
        if closed is None:
            return
        while self._owner.accepting:
            reason = await self._wait_for_close(closed)
            if reason is None or not self._owner.accepting:
                return

            self._cancel_refresh()
            self._ready_generation = -1
            if reason.planned:
                self._status = SocketModeStatus.CONNECTING
            else:
                self._status = SocketModeStatus.DISCONNECTED
                self._owner.geo_disconnected(self.geo, reason.error)

            connection = self._connection
            if connection is not None:
                try:
                    await connection.stop()
                except Exception as error:
                    self._logger.debug("socket-mode[%s]: dropped connection cleanup failed", self.geo, exc_info=error)

            next_closed = await self._reconnect(reason.error)
            if next_closed is None:
                return
            closed = next_closed
            self._status = SocketModeStatus.READY
            if not reason.planned:
                self._owner.geo_reconnected(self.geo)

    async def _wait_for_close(self, closed: asyncio.Future[_CloseReason]) -> Optional[_CloseReason]:
        stop_wait = asyncio.create_task(self._owner.stop_event.wait())
        try:
            done, _ = await asyncio.wait((closed, stop_wait), return_when=asyncio.FIRST_COMPLETED)
            if closed in done:
                return closed.result()
            return None
        finally:
            if not stop_wait.done():
                stop_wait.cancel()
            await asyncio.gather(stop_wait, return_exceptions=True)

    async def _reconnect(self, previous_error: Optional[Exception]) -> Optional[asyncio.Future[_CloseReason]]:
        attempt = 0
        retry_after = self._owner.retry_after_of(previous_error)
        while self._owner.accepting:
            delay = retry_after if retry_after is not None else self._owner.backoff_delay(attempt)
            attempt += 1
            if not await self._owner.sleep(delay) or not self._owner.accepting:
                return None

            self._status = SocketModeStatus.CONNECTING
            generation = self._next_generation()
            try:
                return await self._connect_cycle(generation)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                retry_after = self._owner.retry_after_of(error)
                self._logger.warning(
                    "socket-mode[%s]: reconnect attempt %d failed",
                    self.geo,
                    attempt,
                    exc_info=error,
                )
        return None

    def _schedule_refresh(
        self,
        generation: int,
        expires_in_seconds: Optional[float],
        closed: asyncio.Future[_CloseReason],
    ) -> None:
        """
        Arrange to replace the connection shortly before its credential expires.

        Signalled as a *planned* close so the supervisor reconnects without reporting a
        disconnect, turning a forced auth failure into a routine swap.
        """
        self._cancel_refresh()
        if expires_in_seconds is None or expires_in_seconds <= 0:
            return
        delay = max(expires_in_seconds - self._owner.token_refresh_margin, 1.0)

        async def refresh() -> None:
            try:
                await asyncio.sleep(delay)
                if self._owner.accepting and generation == self._current_generation and not closed.done():
                    closed.set_result(_CloseReason(planned=True))
            except asyncio.CancelledError:
                raise

        self._refresh = asyncio.create_task(
            refresh(),
            name=f"teams-socket-mode-refresh-{self.geo or 'default'}",
        )

    def _cancel_refresh(self) -> None:
        refresh = self._refresh
        self._refresh = None
        if refresh is not None and not refresh.done():
            refresh.cancel()
