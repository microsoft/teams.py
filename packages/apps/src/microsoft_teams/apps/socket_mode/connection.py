"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.

One Socket Mode connection: negotiate, open the socket, complete the SignalR
handshake, wait for ``SocketReady``, then pump activities until it closes.

A connection is deliberately single-use. It never reconnects itself -- on close it
reports ``on_closed`` once and becomes terminal, leaving reconnection to the
supervisor. That keeps retry policy in one place and makes each connection a clean
generation boundary for fencing stale work.

``start()`` is cancellation-safe throughout: every await can be interrupted by the
caller's stop event, and any partially built socket, listener, or heartbeat is torn
down before the error propagates.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, Mapping, Optional, TypeVar, Union, cast

import httpx
from websockets.asyncio.client import connect

from .envelope import parse_envelope, parse_ready_frame
from .negotiate import DEFAULT_NEGOTIATE_TIMEOUT, negotiate_service, negotiate_signalr
from .signalr import (
    SignalRProtocolError,
    encode_hub_message,
    parse_invocation,
    serialize_completion,
    serialize_completion_error,
    split_hub_messages,
)
from .types import (
    SocketActivityEnvelope,
    SocketConnectionHandlers,
    WebSocket,
    WebSocketFactory,
)

logger = logging.getLogger(__name__)
T = TypeVar("T")

DEFAULT_WEBSOCKET_OPEN_TIMEOUT = 15.0
DEFAULT_WEBSOCKET_CLOSE_TIMEOUT = 5.0


class SocketConnectionAborted(RuntimeError):
    """Raised when a stop was requested before the connection finished coming up."""


@dataclass(frozen=True)
class SocketConnectionContext:
    """Everything a :class:`SocketConnection` needs to negotiate and open one socket."""

    negotiate_url: str
    get_bot_token: Callable[[], Awaitable[str]]
    """Acquires the token authenticating the negotiate request, reusing the app's credentials."""

    readiness_timeout: float = 30.0
    keep_alive_interval: float = 15.0
    server_timeout: float = 30.0
    negotiate_timeout: float = DEFAULT_NEGOTIATE_TIMEOUT
    websocket_open_timeout: float = DEFAULT_WEBSOCKET_OPEN_TIMEOUT
    """Bound on opening the socket and completing the SignalR handshake."""


async def _open_websocket(url: str) -> WebSocket:
    return await connect(
        url,
        # The caller bounds this with an abort-aware wait; a second timeout here would
        # silently cap `websocket_open_timeout` at whatever the library default was.
        open_timeout=None,
        ping_interval=None,
        close_timeout=DEFAULT_WEBSOCKET_CLOSE_TIMEOUT,
        max_size=None,
    )


class SignalRSocketConnection:
    """A single negotiated SignalR session over one WebSocket."""

    def __init__(
        self,
        context: SocketConnectionContext,
        handlers: SocketConnectionHandlers,
        *,
        http_client: Optional[httpx.AsyncClient] = None,
        websocket_factory: Optional[WebSocketFactory] = None,
    ):
        self._context = context
        self._handlers = handlers
        self._http_client = http_client
        self._websocket_factory = websocket_factory or _open_websocket
        self._websocket: Optional[WebSocket] = None
        self._listener: Optional[asyncio.Task[None]] = None
        self._heartbeat: Optional[asyncio.Task[None]] = None
        self._send_lock = asyncio.Lock()
        self._stop_event = asyncio.Event()
        self._handshake: Optional[asyncio.Future[None]] = None
        self._ready: Optional[asyncio.Future[None]] = None
        self._stopped = True
        self._closed_notified = False
        self._expires_in_seconds: Optional[float] = None

    @property
    def expires_in_seconds(self) -> Optional[float]:
        return self._expires_in_seconds

    async def start(self, stop_event: Optional[asyncio.Event] = None) -> None:
        """
        Bring the connection up, resolving only once ``SocketReady`` has arrived.

        The sequence is negotiate, open, handshake, then readiness; each step is
        interruptible by ``stop_event``. Any failure tears down whatever was built
        before re-raising, so a failed start never leaves a task or socket behind.
        """
        if not self._stopped:
            raise RuntimeError("Socket Mode connection is already started")
        if stop_event is not None and stop_event.is_set():
            raise SocketConnectionAborted("Socket Mode connect aborted")

        self._stopped = False
        self._closed_notified = False
        self._stop_event = asyncio.Event()
        loop = asyncio.get_running_loop()
        self._handshake = loop.create_future()
        self._ready = loop.create_future()

        try:
            result = await self._wait_interruptibly(
                negotiate_service(
                    self._context.negotiate_url,
                    self._context.get_bot_token,
                    http_client=self._http_client,
                    timeout=self._context.negotiate_timeout,
                ),
                stop_event,
            )
            self._expires_in_seconds = result.expires_in if result.expires_in > 0 else None
            endpoint = await self._wait_interruptibly(
                negotiate_signalr(
                    result.url,
                    result.access_token,
                    http_client=self._http_client,
                    timeout=self._context.negotiate_timeout,
                ),
                stop_event,
            )
            websocket = await self._wait_interruptibly(
                self._websocket_factory(endpoint.url),
                stop_event,
                timeout=self._context.websocket_open_timeout,
            )
            self._websocket = websocket
            logger.debug("Socket Mode WebSocket open; sending SignalR handshake")
            await self._wait_interruptibly(
                websocket.send(encode_hub_message({"protocol": "json", "version": 1})),
                stop_event,
            )
            self._listener = asyncio.create_task(self._listen(), name="teams-socket-mode-listener")
            await self._wait_interruptibly(
                self._handshake,
                stop_event,
                timeout=self._context.websocket_open_timeout,
            )
            logger.debug("Socket Mode SignalR handshake accepted; awaiting SocketReady")
            self._heartbeat = asyncio.create_task(self._send_heartbeats(), name="teams-socket-mode-heartbeat")
            await self._wait_interruptibly(
                self._ready,
                stop_event,
                timeout=self._context.readiness_timeout,
            )
            logger.debug("Socket Mode connection ready")
        except asyncio.TimeoutError as error:
            logger.warning("Socket Mode connection timed out before SocketReady")
            await self.stop()
            raise TimeoutError("Socket Mode connection timed out before SocketReady") from error
        except asyncio.CancelledError:
            await asyncio.shield(self.stop())
            raise
        except Exception:
            await self.stop()
            raise

    async def stop(self) -> None:
        """
        Close the socket and cancel the listener and heartbeat. Safe to call repeatedly,
        and safe to call from inside one of those tasks -- the current task is never
        cancelled by its own cleanup.
        """
        if self._stopped and self._websocket is None:
            return
        self._stopped = True
        self._stop_event.set()

        current = asyncio.current_task()
        internal_tasks = [
            task
            for task in (self._heartbeat, self._listener)
            if task is not None and task is not current and not task.done()
        ]
        for task in internal_tasks:
            task.cancel()
        self._heartbeat = None
        self._listener = None

        websocket = self._websocket
        self._websocket = None
        if websocket is not None:
            try:
                await websocket.close()
            except Exception as error:
                logger.debug("Failed to close Socket Mode WebSocket", exc_info=error)
        if internal_tasks:
            await asyncio.gather(*internal_tasks, return_exceptions=True)

        for future in (self._handshake, self._ready):
            if future is not None and not future.done():
                future.cancel()

    async def _listen(self) -> None:
        """
        Read frames until the socket closes or stop is requested.

        The first frame is always the handshake response; everything after it is a hub
        message. On an unexpected exit the pending gates are failed so ``start()`` cannot
        hang, and ``on_closed`` fires exactly once.
        """
        buffer = ""
        handshake_complete = False
        terminal_error: Optional[Exception] = None
        try:
            while not self._stopped:
                websocket = self._websocket
                if websocket is None:
                    return
                raw = await asyncio.wait_for(websocket.recv(), timeout=self._context.server_timeout)
                if isinstance(raw, bytes):
                    raw = raw.decode("utf-8")
                buffer += raw
                messages, buffer = split_hub_messages(buffer)
                for message in messages:
                    if not handshake_complete:
                        self._complete_handshake(message)
                        handshake_complete = True
                    else:
                        self._handle_hub_message(message)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            terminal_error = error
            logger.debug("Socket Mode listener stopped", exc_info=error)
            self._fail_pending_gates(error)
        finally:
            if not self._stopped:
                websocket = self._websocket
                self._websocket = None
                if websocket is not None:
                    try:
                        await websocket.close()
                    except Exception as error:
                        logger.debug("Failed to close terminated Socket Mode WebSocket", exc_info=error)
                self._notify_closed(terminal_error)

    def _complete_handshake(self, message: object) -> None:
        if not isinstance(message, Mapping):
            raise SignalRProtocolError("SignalR handshake response must be an object")
        fields = cast(Mapping[str, object], message)
        error = fields.get("error")
        if isinstance(error, str) and error:
            raise SignalRProtocolError(f"SignalR handshake failed: {error}")
        if self._handshake is not None and not self._handshake.done():
            self._handshake.set_result(None)

    def _handle_hub_message(self, message: object) -> None:
        fields: Mapping[str, object] = cast(Mapping[str, object], message) if isinstance(message, Mapping) else {}
        if fields.get("type") == 7:
            error = fields.get("error")
            logger.debug("SignalR server closed the connection (error=%s)", error or "none")
            raise SignalRProtocolError(str(error or "SignalR server closed the connection"))

        invocation = parse_invocation(cast(object, message))
        if invocation is None:
            return
        target = invocation.target.lower()
        argument: object = invocation.arguments[0] if invocation.arguments else {}
        if target == "socketready":
            if self._ready is None or self._ready.done() or self._stopped:
                return
            self._ready.set_result(None)
            try:
                self._handlers.on_ready(parse_ready_frame(argument))
            except Exception as error:
                logger.warning("Socket Mode on_ready callback failed", exc_info=error)
            return
        if target == "activity":
            envelope = parse_envelope(argument)
            task = asyncio.create_task(
                self._handle_activity(invocation.invocation_id, envelope),
                name="teams-socket-mode-activity",
            )
            task.add_done_callback(self._activity_finished)

    async def _handle_activity(
        self,
        invocation_id: Optional[str],
        envelope: SocketActivityEnvelope,
    ) -> None:
        try:
            result = await self._handlers.on_activity(envelope)
            if invocation_id is not None and not self._stopped:
                payload = result.model_dump(by_alias=True, exclude_none=True) if result is not None else None
                await self._send(serialize_completion(invocation_id, payload))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            logger.warning("Socket Mode activity handler raised", exc_info=error)
            if invocation_id is not None and not self._stopped:
                await self._send(serialize_completion_error(invocation_id, "Socket Mode activity handler failed"))

    @staticmethod
    def _activity_finished(task: asyncio.Task[None]) -> None:
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.debug("Socket Mode activity task ended after the connection closed", exc_info=error)

    async def _send_heartbeats(self) -> None:
        try:
            while not self._stopped:
                await asyncio.sleep(self._context.keep_alive_interval)
                if not self._stopped:
                    await self._send(encode_hub_message({"type": 6}))
        except asyncio.CancelledError:
            raise
        except Exception as error:
            websocket = self._websocket
            if websocket is not None:
                await websocket.close()
            logger.debug("Socket Mode heartbeat failed", exc_info=error)

    async def _send(self, message: str) -> None:
        async with self._send_lock:
            websocket = self._websocket
            if websocket is None:
                raise ConnectionError("Socket Mode WebSocket is closed")
            await websocket.send(message)

    def _fail_pending_gates(self, error: Exception) -> None:
        """
        Fail whichever of the handshake/readiness gates are still pending.

        When the handshake itself never completed, readiness is cancelled rather than
        failed: the handshake carries the real error, and setting it on both would leave
        one future's exception permanently unretrieved.
        """
        handshake_pending = self._handshake is not None and not self._handshake.done()
        if handshake_pending and self._handshake is not None:
            self._handshake.set_exception(error)
        if self._ready is not None and not self._ready.done():
            if handshake_pending:
                self._ready.cancel()
            else:
                self._ready.set_exception(error)

    def _notify_closed(self, error: Optional[Exception]) -> None:
        if self._closed_notified:
            return
        self._closed_notified = True
        try:
            self._handlers.on_closed(error)
        except Exception as callback_error:
            logger.warning("Socket Mode on_closed callback failed", exc_info=callback_error)

    async def _wait_interruptibly(
        self,
        awaitable: Awaitable[T],
        external_stop: Optional[asyncio.Event],
        *,
        timeout: Optional[float] = None,
    ) -> T:
        """
        Await an operation that can also be ended by stop or a timeout.

        Whichever arm wins, the losers are cancelled and awaited before returning, so no
        orphan task survives the call. Losing to stop raises
        :class:`SocketConnectionAborted`; losing to the timer raises ``TimeoutError``.
        """
        operation = asyncio.ensure_future(awaitable)
        internal_wait = asyncio.create_task(self._stop_event.wait())
        waits: list[Union[asyncio.Future[object], asyncio.Task[object]]] = [operation, internal_wait]
        external_wait: Optional[asyncio.Task[bool]] = None
        timeout_wait: Optional[asyncio.Task[None]] = None
        if external_stop is not None:
            external_wait = asyncio.create_task(external_stop.wait())
            waits.append(external_wait)
        if timeout is not None:
            timeout_wait = asyncio.create_task(asyncio.sleep(timeout))
            waits.append(timeout_wait)
        try:
            done, _ = await asyncio.wait(waits, return_when=asyncio.FIRST_COMPLETED)
            if operation in done:
                return await operation
            operation.cancel()
            await asyncio.gather(operation, return_exceptions=True)
            if timeout_wait is not None and timeout_wait in done:
                raise asyncio.TimeoutError
            raise SocketConnectionAborted("Socket Mode connect aborted")
        except asyncio.CancelledError:
            operation.cancel()
            await asyncio.gather(operation, return_exceptions=True)
            raise
        finally:
            # Gathered one at a time: a heterogeneous splat does not match gather's overloads.
            for task in (internal_wait, external_wait, timeout_wait):
                if task is None:
                    continue
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
