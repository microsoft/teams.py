"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Awaitable, Callable, Optional, Protocol, Union

from pydantic import AliasChoices, AliasGenerator, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel, to_pascal

SOCKET_MODE_PROTOCOL_VERSION = 1
"""
Socket Mode protocol version this SDK speaks. Every reply frame carries it so the
service can detect a mismatch. Bump only in lockstep with the service's
``SocketProtocol.CurrentVersion``.
"""


class SocketModeStatus(StrEnum):
    """
    Lifecycle status of a socket.

    ``READY`` requires more than an open socket: the service must also have pushed
    the ``SocketReady`` frame, which is what admits inbound activities.
    """

    IDLE = "idle"
    CONNECTING = "connecting"
    READY = "ready"
    DISCONNECTED = "disconnected"
    STOPPED = "stopped"


def _inbound_aliases(field: str) -> AliasChoices:
    return AliasChoices(to_camel(field), to_pascal(field))


class _InboundFrame(BaseModel):
    """
    Base for frames read off the wire. The service encodes fields as either camelCase or
    PascalCase depending on the hub protocol, so every field accepts both spellings.
    Unknown fields are kept so a newer service can add them without breaking parsing.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        extra="allow",
        alias_generator=AliasGenerator(validation_alias=_inbound_aliases),
    )


class SocketReadyFrame(_InboundFrame):
    """Pushed once the connection is registered and inbound delivery can begin."""

    bot_key: Optional[str] = None
    connection_id: Optional[str] = None


class SocketActivityEnvelope(_InboundFrame):
    """An inbound activity as delivered on the ``Activity`` hub method."""

    protocol_version: Optional[Union[int, float]] = None
    envelope_id: Optional[str] = None
    """Correlation id echoed back on the reply frame."""

    type: Optional[str] = None
    """``"invoke"`` for invoke activities; the activity type otherwise."""

    ack_required: Optional[bool] = None
    """Set for one-way activities. Invoke activities expect a full result instead."""

    payload: Optional[object] = None
    activity: Optional[object] = None
    """
    Payload alias used by some service builds; read when ``payload`` is absent. Both are
    ``object`` rather than a schema so a malformed activity is caught by the shape check
    that reads them, never by validation that would discard the whole envelope -- and so
    the type checker requires that check before either is used.
    """

    cv: Optional[str] = None
    """MS-CV correlation vector, echoed back for log stitching."""


class ReplyFrame(BaseModel):
    """
    What the handler returns for an envelope. Carries the invoke status and body for an
    invoke, or a bare status-200 acknowledgement for a one-way activity.

    Built in Python rather than read off the wire, so it serializes to camelCase only.
    """

    model_config = ConfigDict(
        frozen=True,
        populate_by_name=True,
        alias_generator=AliasGenerator(serialization_alias=to_camel),
    )

    status: int
    protocol_version: int = SOCKET_MODE_PROTOCOL_VERSION
    envelope_id: Optional[str] = None
    bot_key: Optional[str] = None
    body: Optional[Any] = None
    ts: Optional[int] = None
    """When the reply was produced (epoch ms), for latency telemetry."""

    recv_at: Optional[int] = None
    """When the envelope was received (epoch ms), echoed for telemetry."""


@dataclass(frozen=True)
class SocketConnectionHandlers:
    """Lets a connection drive its supervisor without knowing what the supervisor is."""

    on_activity: Callable[[SocketActivityEnvelope], Awaitable[Optional[ReplyFrame]]]
    """Returns the frame to reply with, or ``None`` to send nothing."""

    on_ready: Callable[[SocketReadyFrame], None]
    on_closed: Callable[[Optional[Exception]], None]
    """Fired exactly once; the connection is terminal afterwards."""


class SocketConnection(Protocol):
    """
    One negotiate plus one SignalR session. A connection is a single generation and never
    reconnects itself: on close it reports ``on_closed`` and becomes terminal, leaving the
    supervisor to decide whether to build a fresh one.
    """

    @property
    def expires_in_seconds(self) -> Optional[float]:
        """Lifetime of the negotiate token, or ``None`` when unknown."""
        ...

    async def start(self, stop_event: Optional[asyncio.Event] = None) -> None:
        """
        Resolve once ``SocketReady`` has been received. Raises if the socket fails to open,
        readiness times out, or ``stop_event`` is set first.
        """
        ...

    async def stop(self) -> None:
        """Close the connection. Safe to call more than once."""
        ...


class WebSocket(Protocol):
    """The slice of the websockets client the connection uses, narrowed so tests can mock it."""

    async def send(self, message: str) -> None: ...

    async def recv(self) -> Union[str, bytes]: ...

    async def close(self) -> None: ...


WebSocketFactory = Callable[[str], Awaitable[WebSocket]]
ConnectionFactory = Callable[[str, SocketConnectionHandlers], SocketConnection]


@dataclass(frozen=True)
class SocketModeCallbacks:
    """Optional lifecycle observers. Each receives the geo the event came from."""

    on_ready: Optional[Callable[[str, SocketReadyFrame], None]] = None
    on_disconnected: Optional[Callable[[str, Optional[Exception]], None]] = None
    on_reconnected: Optional[Callable[[str], None]] = None
