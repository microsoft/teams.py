"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import ast
import json
from pathlib import Path

import pytest
from microsoft_teams.apps.socket_mode import signalr
from microsoft_teams.apps.socket_mode.signalr import (
    RECORD_SEPARATOR,
    SignalRProtocolError,
    parse_hub_messages,
    parse_invocation,
    serialize_completion,
)


def test_incomplete_chunk_fails_closed():
    """Matches the SignalR JS client: a chunk not ending on a separator is rejected."""
    with pytest.raises(SignalRProtocolError, match="incomplete"):
        parse_hub_messages('{"type":6}\u001e{"type":')


def test_multiple_frames_in_one_chunk_are_all_parsed():
    messages = parse_hub_messages(f'{{"type":6}}{RECORD_SEPARATOR}{{"type":3}}{RECORD_SEPARATOR}')

    assert messages == [{"type": 6}, {"type": 3}]


def test_invalid_hub_json_fails_closed():
    with pytest.raises(SignalRProtocolError, match="invalid JSON"):
        parse_hub_messages(f"not-json{RECORD_SEPARATOR}")


def test_malformed_invocation_fails_closed():
    with pytest.raises(SignalRProtocolError, match="missing target"):
        parse_invocation({"type": 1, "target": "Activity"})


def test_invocation_id_is_optional():
    invocation = parse_invocation({"type": 1, "target": "Activity", "arguments": [{"envelopeId": "env-1"}]})

    assert invocation is not None
    assert invocation.invocation_id is None
    assert invocation.arguments == ({"envelopeId": "env-1"},)


def test_non_string_invocation_id_fails_closed():
    """Absent means fire-and-forget; a non-string is malformed and must not look the same."""
    with pytest.raises(SignalRProtocolError, match="invalid invocationId"):
        parse_invocation({"type": 1, "target": "Activity", "arguments": [], "invocationId": 42})


def test_completion_wraps_result_and_terminates_the_frame():
    completion = serialize_completion("inv-1", {"protocolVersion": 1, "status": 202})

    assert completion.endswith(RECORD_SEPARATOR)
    payload = json.loads(completion.removesuffix(RECORD_SEPARATOR))
    assert payload == {"type": 3, "invocationId": "inv-1", "result": {"protocolVersion": 1, "status": 202}}


def test_completion_without_a_result_omits_the_key():
    payload = json.loads(serialize_completion("inv-1", None).removesuffix(RECORD_SEPARATOR))

    assert payload == {"type": 3, "invocationId": "inv-1"}


def test_signalr_layer_stays_free_of_socket_mode_imports():
    """
    This module is a stand-in for a SignalR client library we do not have. Keeping it
    free of sibling imports is what makes it replaceable, so guard that boundary.
    """
    tree = ast.parse(Path(signalr.__file__).read_text(encoding="utf-8"))
    relative_imports = [node for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and (node.level or 0) > 0]

    assert relative_imports == []


def test_unused_frame_types_are_ignored_rather_than_fatal():
    """
    Forward compatibility: the service may add frame types this transport does not use
    (streaming, stateful reconnect). They must degrade to a no-op, not kill the listener.
    """
    for frame_type in (2, 3, 4, 5, 6, 8, 9):
        assert parse_invocation({"type": frame_type, "target": "X", "arguments": []}) is None
