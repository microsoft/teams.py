"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Keeps one geography connected: initial connect within a startup budget, then
# supervision that reconnects with backoff for as long as the transport is accepting.
#
# Each connection attempt gets a monotonically increasing *generation*. Because a
# replaced connection's in-flight callbacks can still fire, generations are what make
# stale work identifiable.
#
# A credential refresh is a *make-before-break* swap: the live connection keeps serving
# while its replacement negotiates and reaches ``SocketReady``. Only then is the old one
# retired, and even then it stays open briefly because the service can keep routing to a
# cached connection id for a short window after the handoff. Dispatch is therefore allowed
# from the active generation and from any still-retiring one; everything else is refused.

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

    def is_terminal(self, error: Optional[Exception]) -> bool: ...

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


@dataclass(frozen=True)
class _ActiveConnection:
    generation: int
    connection: SocketConnection


CONNECTION_HANDOFF_SECONDS = 5.0
"""How long a superseded connection stays open so cached routing to it can drain."""


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
        self._active: Optional[_ActiveConnection] = None
        self._retiring: dict[int, SocketConnection] = {}
        self._retire_tasks: set[asyncio.Task[None]] = set()
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

        Accepts the active connection and any predecessor still inside its handoff window,
        so a rotation does not drop activities the service routed to the old connection id.
        Anything older, or anything arriving once the transport stops accepting, is refused.
        """
        if not self._owner.accepting:
            return False
        active = self._active
        return (active is not None and active.generation == generation) or generation in self._retiring

    async def start_initial(self) -> None:
        """
        Establish the first connection, retrying until the startup budget is spent.

        Raises the last error once the budget is exhausted, so a geo that never comes up
        fails ``start()`` rather than silently degrading.
        """
        self._status = SocketModeStatus.CONNECTING
        deadline = asyncio.get_running_loop().time() + self._owner.startup_timeout
        bounded = self._owner.startup_timeout > 0
        attempt = 0
        last_error: Optional[Exception] = None

        while self._owner.accepting:
            generation = self._next_generation()
            # The per-step timeouts can sum to more than the budget, so bound the attempt
            # by whatever is left of it. `None` means unbounded, which is what the single
            # attempt of a zero budget gets.
            remaining = deadline - asyncio.get_running_loop().time() if bounded else None
            if remaining is not None and remaining <= 0:
                break
            try:
                async with asyncio.timeout(remaining):
                    self._closed = await self._connect_cycle(generation)
                self._status = SocketModeStatus.READY
                return
            except asyncio.CancelledError:
                raise
            except Exception as error:
                # Running out of budget says nothing about why the connection failed, so
                # a cut-off attempt must not replace an earlier error that does.
                if last_error is None or asyncio.get_running_loop().time() < deadline:
                    last_error = error
                if not self._owner.accepting:
                    break
                if self._owner.is_terminal(error):
                    raise
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
        """Tear down the refresh timer, every owned connection, and the supervisor."""
        self._cancel_refresh()
        for task in tuple(self._retire_tasks):
            task.cancel()
        if self._retire_tasks:
            await asyncio.gather(*self._retire_tasks, return_exceptions=True)
            self._retire_tasks.clear()

        active = self._active
        connections = ([active.connection] if active is not None else []) + list(self._retiring.values())
        self._active = None
        self._retiring.clear()
        for connection in connections:
            try:
                await connection.stop()
            except Exception as error:
                self._logger.debug("socket-mode[%s]: connection stop failed", self.geo, exc_info=error)

        supervisor = self._supervisor
        self._supervisor = None
        if supervisor is not None and supervisor is not asyncio.current_task() and not supervisor.done():
            supervisor.cancel()
            await asyncio.gather(supervisor, return_exceptions=True)
        self._status = SocketModeStatus.STOPPED

    def _next_generation(self) -> int:
        self._generation += 1
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
            if generation != self._generation or not self._owner.accepting:
                return
            # Promote this generation and demote its predecessor to the handoff window
            # rather than dropping it, so in-flight routing to the old id still lands.
            active = self._active
            if active is not None and active.generation != generation:
                self._retiring[active.generation] = active.connection
            self._active = _ActiveConnection(generation=generation, connection=connection)
            self._status = SocketModeStatus.READY
            self._owner.geo_ready(self.geo, frame)

        def on_closed(error: Optional[Exception]) -> None:
            active = self._active
            if active is not None and active.generation == generation:
                self._cancel_refresh()
                # A planned rotation already resolved `closed` and moved the supervisor on.
                # If the still-serving predecessor dies before its replacement is ready,
                # there is a real delivery gap and it has to be reported.
                if closed.done() and self._owner.accepting:
                    self._active = None
                    self._report_disconnected(error)
            self._retiring.pop(generation, None)
            if not closed.done():
                closed.set_result(_CloseReason(planned=False, error=error))

        handlers = SocketConnectionHandlers(
            on_activity=on_activity,
            on_ready=on_ready,
            on_closed=on_closed,
        )
        connection = self._owner.create_connection(self._negotiate_url, handlers)
        try:
            await connection.start(self._owner.stop_event)
        except BaseException:
            try:
                await connection.stop()
            except Exception as error:
                self._logger.debug("socket-mode[%s]: failed connection cleanup", self.geo, exc_info=error)
            raise

        active = self._active
        if active is None or active.generation != generation:
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
            previous = self._active if reason.planned else None
            if not reason.planned:
                self._report_disconnected(reason.error)
                dropped = self._active
                self._active = None
                if dropped is not None:
                    try:
                        await dropped.connection.stop()
                    except Exception as error:
                        self._logger.debug(
                            "socket-mode[%s]: dropped connection cleanup failed", self.geo, exc_info=error
                        )

            next_closed = await self._reconnect(reason.error, keep_serving=reason.planned)
            if next_closed is None:
                return
            closed = next_closed
            self._status = SocketModeStatus.READY
            if (
                reason.planned
                and previous is not None
                and self._retiring.get(previous.generation) is previous.connection
            ):
                self._schedule_retire(previous)
                self._logger.info("socket-mode[%s]: token rotated; inbound delivery continues for this geo", self.geo)
            else:
                # Either an unplanned drop, or a rotation whose predecessor died before the
                # replacement was ready -- both are visible outages that have now recovered.
                self._logger.info("socket-mode[%s]: reconnected; inbound delivery resumed for this geo", self.geo)
                self._owner.geo_reconnected(self.geo)

    def _report_disconnected(self, error: Optional[Exception]) -> None:
        self._status = SocketModeStatus.DISCONNECTED
        self._logger.warning(
            "socket-mode[%s]: disconnected; inbound delivery paused for this geo",
            self.geo,
            exc_info=error,
        )
        self._owner.geo_disconnected(self.geo, error)

    def _schedule_retire(self, previous: _ActiveConnection) -> None:
        task = asyncio.create_task(
            self._retire(previous),
            name=f"teams-socket-mode-retire-{self.geo or 'default'}",
        )
        self._retire_tasks.add(task)
        task.add_done_callback(self._retire_tasks.discard)

    async def _retire(self, previous: _ActiveConnection) -> None:
        """Close a superseded connection once its handoff window has elapsed."""
        if not await self._owner.sleep(CONNECTION_HANDOFF_SECONDS):
            return
        if self._retiring.get(previous.generation) is not previous.connection:
            return
        del self._retiring[previous.generation]
        try:
            await previous.connection.stop()
        except Exception as error:
            self._logger.debug("socket-mode[%s]: retired connection cleanup failed", self.geo, exc_info=error)

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

    async def _reconnect(
        self, previous_error: Optional[Exception], *, keep_serving: bool = False
    ) -> Optional[asyncio.Future[_CloseReason]]:
        attempt = 0
        retry_after = self._owner.retry_after_of(previous_error)
        while self._owner.accepting:
            delay = retry_after if retry_after is not None else self._owner.backoff_delay(attempt)
            attempt += 1
            if not await self._owner.sleep(delay) or not self._owner.accepting:
                return None

            # A rotation still has a live connection serving, so reporting `connecting`
            # would understate the geo's availability.
            if not keep_serving:
                self._status = SocketModeStatus.CONNECTING
            generation = self._next_generation()
            try:
                return await self._connect_cycle(generation)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                if self._owner.is_terminal(error):
                    self._logger.error(
                        "socket-mode[%s]: reconnect rejected; giving up on this geo",
                        self.geo,
                        exc_info=error,
                    )
                    await self.stop()
                    self._report_disconnected(error)
                    return None
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
                active = self._active
                if (
                    self._owner.accepting
                    and active is not None
                    and active.generation == generation
                    and not closed.done()
                ):
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
