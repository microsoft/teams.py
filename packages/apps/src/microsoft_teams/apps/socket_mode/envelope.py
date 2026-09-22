"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

# Mapping between Socket Mode wire frames and the Teams domain: inbound activity
# envelopes in, reply frames out.
#
# Casing and field validation are handled declaratively by the models in
# :mod:`types`, so this module is only the logic that cannot be expressed as a
# schema -- deciding which field actually holds the activity, and classifying an
# envelope as invoke versus one-way.

import time
from typing import Any, Mapping, Optional, TypeGuard, cast

from pydantic import ValidationError

from .types import ReplyFrame, SocketActivityEnvelope, SocketReadyFrame


class EnvelopeError(ValueError):
    """An inbound frame did not match the Socket Mode envelope contract."""


def parse_envelope(value: object) -> SocketActivityEnvelope:
    """
    Build an envelope from a decoded ``Activity`` argument.

    Rejects a frame whose metadata is malformed rather than nulling the offending field:
    a dropped ``envelope_id`` would produce a reply the service cannot correlate, turning
    a visible error into a silent one. The activity itself is deliberately untyped here
    and shape-checked by :func:`read_envelope_activity` instead.
    """
    try:
        return SocketActivityEnvelope.model_validate(value)
    except ValidationError as error:
        raise EnvelopeError("Socket Mode activity envelope must be an object") from error


def parse_ready_frame(value: object) -> SocketReadyFrame:
    """
    Build a ``SocketReady`` frame from its decoded argument.

    Every field is optional, so a malformed argument yields an empty frame rather than an
    error: readiness itself is signalled by the frame's arrival, not its contents.
    """
    try:
        return SocketReadyFrame.model_validate(value)
    except ValidationError:
        return SocketReadyFrame()


def read_envelope_activity(envelope: SocketActivityEnvelope) -> Optional[Mapping[str, Any]]:
    """
    Extract the activity, which rides under ``payload`` or ``activity`` depending on the
    service build. Each candidate is shape-checked so a malformed ``payload`` falls
    through to ``activity`` instead of masking it.
    """
    if _is_activity(envelope.payload):
        return envelope.payload
    if _is_activity(envelope.activity):
        return envelope.activity
    return None


def _is_activity(value: object) -> TypeGuard[Mapping[str, Any]]:
    """Whether a value is shaped like an activity: an object carrying a string ``type``."""
    if not isinstance(value, Mapping):
        return False
    fields = cast(Mapping[str, object], value)
    return isinstance(fields.get("type"), str)


def is_invoke_envelope(envelope: SocketActivityEnvelope) -> bool:
    """
    Whether the envelope expects a full invoke result rather than an acknowledgement.

    Classified by activity type only. ``ack_required`` is a delivery concern and
    deliberately does not affect this: an invoke still owes a status and body even when
    an acknowledgement was also requested.
    """
    if envelope.type:
        return envelope.type.lower() == "invoke"
    activity = read_envelope_activity(envelope)
    return activity is not None and str(activity.get("type", "")).lower() == "invoke"


def build_reply_frame(
    envelope: SocketActivityEnvelope,
    *,
    bot_key: Optional[str],
    status: int = 200,
    body: Optional[object] = None,
    received_at: Optional[int] = None,
) -> ReplyFrame:
    """Build the reply for an envelope, stamping the timestamps used for latency telemetry."""
    now = int(time.time() * 1000)
    return ReplyFrame(
        envelope_id=envelope.envelope_id,
        bot_key=bot_key,
        status=status,
        body=body,
        recv_at=received_at or now,
        ts=now,
    )
