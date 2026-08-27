"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from microsoft_teams.apps import TurnState, TurnStateContainer
from microsoft_teams.apps.oauth_state import (
    PendingOAuthSignIn,
    clear_pending_oauth_sign_in,
    get_pending_oauth_sign_ins,
    mark_pending_oauth_sso_consumed,
    record_pending_oauth_sign_in,
    replace_pending_oauth_sign_ins,
)


def make_state(user_data: dict[str, Any] | None = None) -> TurnStateContainer:
    return TurnStateContainer(
        conversation=TurnState(),
        conversation_id="conv-1",
        user=TurnState(user_data),
        user_id="user-1",
    )


def stored_keys(state: TurnStateContainer) -> set[str]:
    assert state.user is not None
    return {key for key in state.user if key.startswith("__oauth:pending:")}


def iso(epoch_seconds: float) -> str:
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).isoformat()


class TestPendingSignInStorageLayout:
    def test_records_one_key_per_connection_holding_an_iso_timestamp(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "Graph", sso_offered=False)

        assert stored_keys(state) == {"__oauth:pending:Graph"}
        assert state.user is not None
        stored = state.user["__oauth:pending:Graph"]
        assert isinstance(stored, str)
        assert datetime.fromisoformat(stored).tzinfo is not None

    def test_offering_sso_adds_a_sibling_marker_sharing_the_timestamp(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "Graph", sso_offered=True)

        assert stored_keys(state) == {"__oauth:pending:Graph", "__oauth:pending:sso:Graph"}
        assert state.user is not None
        assert state.user["__oauth:pending:sso:Graph"] == state.user["__oauth:pending:Graph"]

    def test_connection_casing_is_stored_verbatim(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "GitHub", sso_offered=True)

        assert stored_keys(state) == {"__oauth:pending:GitHub", "__oauth:pending:sso:GitHub"}
        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["GitHub"]


class TestDotNetTimestampInterop:
    """Every ``DateTimeOffset`` shape .NET emits must round-trip through the reader."""

    @pytest.mark.parametrize(
        "shape",
        ["dotnet_7_digit_fraction", "zulu_suffix", "no_fraction", "non_utc_offset", "no_offset"],
    )
    def test_reads_timestamps_written_by_the_csharp_sdk(self, shape: str) -> None:
        moment = datetime.now(timezone.utc).replace(microsecond=214000)
        if shape == "dotnet_7_digit_fraction":
            # System.Text.Json writes 7 fractional digits, which Python truncates to 6.
            raw = moment.isoformat().replace("+00:00", "0+00:00")
        elif shape == "zulu_suffix":
            raw = moment.isoformat().replace("+00:00", "Z")
        elif shape == "no_fraction":
            moment = moment.replace(microsecond=0)
            raw = moment.isoformat()
        elif shape == "non_utc_offset":
            raw = moment.astimezone(timezone(timedelta(hours=-7))).isoformat()
        else:
            # No offset at all is read as UTC.
            raw = moment.replace(tzinfo=None).isoformat()

        state = make_state({"__oauth:pending:Graph": raw})
        pending = get_pending_oauth_sign_ins(state)

        assert [hint.connection_name for hint in pending] == ["Graph"]
        assert pending[0].created_at == pytest.approx(moment.timestamp())


class TestPendingSignInLookup:
    def test_lookup_is_case_insensitive_while_preserving_stored_casing(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "GitHub", sso_offered=True)

        clear_pending_oauth_sign_in(state, "github")

        assert stored_keys(state) == set()

    def test_recording_again_replaces_an_earlier_attempt_under_different_casing(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "GitHub", sso_offered=True)
        record_pending_oauth_sign_in(state, "github", sso_offered=False)

        # Exactly one attempt survives, under the casing that was recorded last, and
        # the stale SSO marker from the first attempt does not linger.
        assert stored_keys(state) == {"__oauth:pending:github"}
        assert [(h.connection_name, h.sso_offered) for h in get_pending_oauth_sign_ins(state)] == [("github", False)]

    def test_duplicate_casing_keeps_the_newer_attempt_deterministically(self) -> None:
        now = time.time()
        # We never write two casings for one connection, but another SDK might.
        state = make_state(
            {
                "__oauth:pending:GitHub": iso(now - 30),
                "__oauth:pending:github": iso(now),
            }
        )

        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["github"]
        # The losing key is dropped rather than left to linger until it expires.
        assert stored_keys(state) == {"__oauth:pending:github"}

    def test_hints_are_returned_newest_first(self) -> None:
        now = time.time()
        state = make_state(
            {
                "__oauth:pending:older": iso(now - 30),
                "__oauth:pending:newest": iso(now),
                "__oauth:pending:middle": iso(now - 10),
            }
        )

        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == [
            "newest",
            "middle",
            "older",
        ]

    def test_equal_timestamps_break_ties_deterministically(self) -> None:
        stamp = iso(time.time())
        state = make_state({"__oauth:pending:beta": stamp, "__oauth:pending:alpha": stamp})

        # Storage order must not leak into the result.
        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["alpha", "beta"]


class TestSsoMarkerHandling:
    def test_marking_sso_consumed_retires_only_the_sso_marker(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "Graph", sso_offered=True)
        assert state.user is not None
        original = state.user["__oauth:pending:Graph"]

        mark_pending_oauth_sso_consumed(state, "graph")

        # The sign-in is still pending on its original schedule; only SSO is spent.
        assert stored_keys(state) == {"__oauth:pending:Graph"}
        assert state.user["__oauth:pending:Graph"] == original
        assert [(h.connection_name, h.sso_offered) for h in get_pending_oauth_sign_ins(state)] == [("Graph", False)]

    def test_connection_named_sso_is_not_mistaken_for_an_sso_marker(self) -> None:
        # ``sso:`` is a legal start to a connection name. Without its own base marker,
        # ``__oauth:pending:sso:graph`` is the marker for a connection called "sso:graph".
        state = make_state({"__oauth:pending:sso:graph": iso(time.time())})

        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["sso:graph"]

        clear_pending_oauth_sign_in(state, "sso:graph")
        assert stored_keys(state) == set()

    def test_sso_marker_is_recognised_when_its_base_marker_exists(self) -> None:
        stamp = iso(time.time())
        state = make_state({"__oauth:pending:graph": stamp, "__oauth:pending:sso:graph": stamp})

        assert [(h.connection_name, h.sso_offered) for h in get_pending_oauth_sign_ins(state)] == [("graph", True)]

    def test_orphaned_sso_marker_is_dropped_when_its_sign_in_expires(self) -> None:
        now = time.time()
        state = make_state(
            {
                "__oauth:pending:graph": iso(now - 301),
                "__oauth:pending:sso:graph": iso(now),
            }
        )

        assert get_pending_oauth_sign_ins(state) == []
        # An SSO marker must not outlive the sign-in it describes.
        assert stored_keys(state) == set()


class TestPendingSignInPruning:
    @pytest.mark.parametrize("bad_value", [["not-a-string"], 12345, None, "not-a-timestamp", ""])
    def test_a_single_bad_key_does_not_discard_healthy_ones(self, bad_value: Any) -> None:
        state = make_state(
            {
                "__oauth:pending:broken": bad_value,
                "__oauth:pending:healthy": iso(time.time()),
            }
        )

        # The per-key layout limits the blast radius: only the bad key is dropped.
        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["healthy"]
        assert stored_keys(state) == {"__oauth:pending:healthy"}

    def test_state_from_an_earlier_layout_reads_as_absent(self) -> None:
        legacy = {"version": 1, "hints": [{"connection_name": "GitHub", "created_at": time.time()}]}
        state = make_state({"__oauth:pending": legacy, "__oauth:pending:healthy": iso(time.time())})

        # The earlier layout kept every hint in one `__oauth:pending` document. That key
        # has no trailing separator, so the prefix scan never sees it: it reads as absent
        # and sign-in simply starts over. Nothing needs migrating, and nothing else is
        # disturbed by leftovers.
        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["healthy"]
        assert state.user is not None
        assert state.user["__oauth:pending"] == legacy

    def test_expired_and_future_dated_markers_are_pruned_on_read(self) -> None:
        now = time.time()
        state = make_state(
            {
                "__oauth:pending:stale": iso(now - 301),
                "__oauth:pending:future": iso(now + 61),
                "__oauth:pending:live": iso(now - 30),
            }
        )

        assert [hint.connection_name for hint in get_pending_oauth_sign_ins(state)] == ["live"]
        assert stored_keys(state) == {"__oauth:pending:live"}

    def test_recording_prunes_expired_markers_left_by_other_connections(self) -> None:
        state = make_state({"__oauth:pending:abandoned": iso(time.time() - 301)})

        record_pending_oauth_sign_in(state, "Graph", sso_offered=False)

        # Long-lived user state must not accumulate sign-ins that were never completed.
        assert stored_keys(state) == {"__oauth:pending:Graph"}

    def test_clearing_without_a_connection_removes_every_marker(self) -> None:
        state = make_state({"unrelated": "keep me"})
        record_pending_oauth_sign_in(state, "Graph", sso_offered=True)
        record_pending_oauth_sign_in(state, "GitHub", sso_offered=False)

        clear_pending_oauth_sign_in(state)

        assert stored_keys(state) == set()
        assert state.user is not None
        assert state.user["unrelated"] == "keep me"


class TestReplacePendingSignIns:
    def test_replacing_rewrites_the_stored_layout(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "Graph", sso_offered=True)
        now = time.time()

        replace_pending_oauth_sign_ins(
            state,
            [PendingOAuthSignIn(connection_name="GitHub", created_at=now, sso_offered=True)],
        )

        assert stored_keys(state) == {"__oauth:pending:GitHub", "__oauth:pending:sso:GitHub"}
        restored = get_pending_oauth_sign_ins(state)
        assert [(h.connection_name, h.sso_offered) for h in restored] == [("GitHub", True)]
        assert restored[0].created_at == pytest.approx(now, abs=1e-6)

    def test_replacing_with_an_empty_list_clears_everything(self) -> None:
        state = make_state()
        record_pending_oauth_sign_in(state, "Graph", sso_offered=True)

        replace_pending_oauth_sign_ins(state, [])

        assert stored_keys(state) == set()


class TestMissingState:
    """Every helper tolerates absent state, so OAuth works without a state store."""

    def test_helpers_are_no_ops_without_state(self) -> None:
        assert get_pending_oauth_sign_ins(None) == []
        record_pending_oauth_sign_in(None, "Graph", sso_offered=True)
        clear_pending_oauth_sign_in(None, "Graph")
        mark_pending_oauth_sso_consumed(None, "Graph")
        replace_pending_oauth_sign_ins(None, [])

    def test_helpers_are_no_ops_without_a_user_scope(self) -> None:
        state = TurnStateContainer(
            conversation=TurnState(),
            conversation_id="conv-1",
            user=None,
            user_id=None,
        )

        assert get_pending_oauth_sign_ins(state) == []
        record_pending_oauth_sign_in(state, "Graph", sso_offered=True)
        clear_pending_oauth_sign_in(state, "Graph")
        mark_pending_oauth_sso_consumed(state, "Graph")
        replace_pending_oauth_sign_ins(state, [])
