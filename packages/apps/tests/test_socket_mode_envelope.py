"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.apps.socket_mode.envelope import (
    EnvelopeError,
    build_reply_frame,
    is_invoke_envelope,
    parse_envelope,
    read_envelope_activity,
)


def test_envelope_accepts_pascal_case_and_validates_activity_shape():
    envelope = parse_envelope(
        {
            "ProtocolVersion": 1,
            "EnvelopeId": "env-1",
            "Type": "invoke",
            "Payload": "invalid",
            "Activity": {"type": "invoke", "name": "card/action"},
        }
    )

    assert envelope.protocol_version == 1
    assert envelope.envelope_id == "env-1"
    assert read_envelope_activity(envelope) == {"type": "invoke", "name": "card/action"}
    assert is_invoke_envelope(envelope)


def test_malformed_correlation_field_is_rejected_rather_than_silently_dropped():
    """
    A junk ``envelopeId`` must fail loudly. Coercing it to ``None`` would send a reply the
    service cannot correlate, turning a visible error into a silent one.
    """
    with pytest.raises(EnvelopeError):
        parse_envelope({"envelopeId": 123, "payload": {"type": "message"}})


def test_malformed_payload_does_not_reject_the_envelope():
    """The activity is shape-checked on read, so a junk payload falls through to ``activity``."""
    envelope = parse_envelope({"payload": "junk", "activity": {"type": "message"}})

    assert read_envelope_activity(envelope) == {"type": "message"}


def test_invoke_classification_falls_back_to_activity_type():
    assert is_invoke_envelope(parse_envelope({"payload": {"type": "invoke"}}))
    assert not is_invoke_envelope(parse_envelope({"payload": {"type": "message"}, "ackRequired": True}))


def test_reply_frame_is_versioned_and_omits_unset_fields():
    envelope = parse_envelope({"envelopeId": "env-1", "payload": {"type": "message"}})

    payload = build_reply_frame(envelope, bot_key="bot-1", status=202).model_dump(by_alias=True, exclude_none=True)

    assert payload["protocolVersion"] == 1
    assert payload["status"] == 202
    assert payload["envelopeId"] == "env-1"
    assert payload["botKey"] == "bot-1"
    assert "body" not in payload


def test_invoke_classification_ignores_ack_required():
    """``ackRequired`` is a delivery concern: an invoke still owes a full result."""
    assert is_invoke_envelope(parse_envelope({"type": "invoke", "ackRequired": True}))
    assert is_invoke_envelope(parse_envelope({"payload": {"type": "invoke"}, "ackRequired": True}))


def test_activity_is_none_when_neither_field_is_activity_shaped():
    assert read_envelope_activity(parse_envelope({"payload": "junk", "activity": {"no": "type"}})) is None
