"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# The subset of the SignalR JSON hub protocol this transport needs, hand-rolled
# because Microsoft ships no SignalR client for Python.
#
# This module deliberately knows nothing about Teams and imports nothing from this
# SDK, so it can be replaced wholesale if an official client appears. A test
# enforces that boundary by rejecting any relative import here.
#
# Frames are JSON objects separated by :data:`RECORD_SEPARATOR`, discriminated by a
# numeric ``type``: ``1`` invocation, ``3`` completion, ``6`` ping, ``7`` close. The
# handshake is the one exception -- it carries no ``type`` and is handled by the caller.

import json
from dataclasses import dataclass
from typing import Mapping, Optional, cast

RECORD_SEPARATOR = "\x1e"
"""Terminator the SignalR JSON hub protocol appends to every frame."""


class SignalRProtocolError(ValueError):
    """The peer sent something the SignalR JSON hub protocol does not allow."""


@dataclass(frozen=True)
class SignalRInvocation:
    """A type-1 frame: the server calling a method on this client."""

    target: str
    arguments: tuple[object, ...]
    invocation_id: Optional[str] = None
    """Present when the server expects a completion carrying a client result."""


def encode_hub_message(message: Mapping[str, object]) -> str:
    """Serialize one frame, compactly, with the record separator appended."""
    return json.dumps(message, separators=(",", ":")) + RECORD_SEPARATOR


def split_hub_messages(buffer: str) -> tuple[list[object], str]:
    """
    Split complete frames off a receive buffer, returning them and the partial tail.

    A WebSocket read can end mid-frame, so the trailing segment is handed back to be
    prepended to the next read rather than parsed.
    """
    segments = buffer.split(RECORD_SEPARATOR)
    remainder = segments.pop()
    messages: list[object] = []
    for segment in segments:
        if not segment:
            continue
        try:
            messages.append(json.loads(segment))
        except json.JSONDecodeError as error:
            raise SignalRProtocolError("SignalR frame contains invalid JSON") from error
    return messages, remainder


def parse_invocation(message: object) -> Optional[SignalRInvocation]:
    """
    Return the invocation for a type-1 frame, or ``None`` when it is a different frame.

    ``None`` means "not an invocation" (a ping, say) and is routine;
    :class:`SignalRProtocolError` means the frame claimed to be one but was malformed.
    """
    if not isinstance(message, Mapping):
        return None
    fields = cast(Mapping[str, object], message)
    if fields.get("type") != 1:
        return None
    target = fields.get("target")
    arguments = fields.get("arguments")
    if not isinstance(target, str) or not isinstance(arguments, list):
        raise SignalRProtocolError("SignalR invocation is missing target or arguments")
    invocation_id = fields.get("invocationId")
    return SignalRInvocation(
        target=target,
        arguments=tuple(cast(list[object], arguments)),
        invocation_id=invocation_id if isinstance(invocation_id, str) else None,
    )


def serialize_completion(invocation_id: str, result: Optional[Mapping[str, object]]) -> str:
    """
    Build the type-3 completion answering an invocation.

    ``result`` is an already-serialized mapping rather than a domain object, which is
    what keeps this module free of Teams types.
    """
    message: dict[str, object] = {"type": 3, "invocationId": invocation_id}
    if result is not None:
        message["result"] = result
    return encode_hub_message(message)


def serialize_completion_error(invocation_id: str, error: str) -> str:
    """Build the type-3 completion reporting that the invocation failed."""
    return encode_hub_message({"type": 3, "invocationId": invocation_id, "error": error})
