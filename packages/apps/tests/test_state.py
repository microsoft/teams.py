"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import time

import pytest
from microsoft_teams.apps.state import (
    StateOptions,
    TurnState,
    TurnStateContainer,
    TurnStateLoader,
    TurnStateSealedError,
)
from microsoft_teams.common import LocalStorage

# ---------------------------------------------------------------------------
# TurnState
# ---------------------------------------------------------------------------


class TestTurnState:
    def test_starts_clean_and_empty(self):
        state = TurnState()
        assert state.is_dirty is False
        assert state.is_empty is True
        assert len(state) == 0

    def test_seeded_data_is_clean(self):
        state = TurnState({"a": 1})
        assert state.is_dirty is False
        assert state.is_empty is False
        assert state["a"] == 1

    def test_set_marks_dirty(self):
        state = TurnState()
        state["x"] = 1
        assert state.is_dirty is True
        assert state.is_empty is False

    def test_delete_marks_dirty(self):
        state = TurnState({"x": 1})
        del state["x"]
        assert state.is_dirty is True
        assert state.is_empty is True

    def test_read_does_not_mark_dirty(self):
        state = TurnState({"x": 1})
        _ = state["x"]
        _ = "x" in state
        _ = list(state)
        _ = len(state)
        assert state.is_dirty is False

    def test_mapping_protocol(self):
        state = TurnState()
        state.update({"a": 1, "b": 2})
        assert dict(state) == {"a": 1, "b": 2}
        assert sorted(state) == ["a", "b"]
        assert state.get("missing") is None
        assert state.pop("a") == 1
        assert "a" not in state

    def test_to_dict_returns_copy(self):
        state = TurnState({"a": 1})
        snapshot = state.to_dict()
        snapshot["a"] = 999
        assert state["a"] == 1  # original untouched

    def test_seal_blocks_access(self):
        state = TurnState({"a": 1})
        state.seal()
        assert state.is_sealed is True
        with pytest.raises(TurnStateSealedError):
            _ = state["a"]
        with pytest.raises(TurnStateSealedError):
            state["b"] = 2
        with pytest.raises(TurnStateSealedError):
            del state["a"]
        with pytest.raises(TurnStateSealedError):
            _ = "a" in state
        with pytest.raises(TurnStateSealedError):
            _ = list(state)

    def test_seal_still_allows_metadata(self):
        state = TurnState({"a": 1})
        state["b"] = 2
        state.seal()
        # Diagnostics remain readable after sealing.
        assert state.is_sealed is True
        assert state.is_dirty is True
        assert state.is_empty is False
        assert len(state) == 2


# ---------------------------------------------------------------------------
# TurnStateContainer
# ---------------------------------------------------------------------------


class TestTurnStateContainer:
    def test_seal_seals_both_scopes(self):
        container = TurnStateContainer(conversation=TurnState(), user=TurnState())
        container.seal()
        assert container.conversation.is_sealed
        assert container.user is not None and container.user.is_sealed

    def test_seal_tolerates_missing_user(self):
        container = TurnStateContainer(conversation=TurnState(), user=None)
        container.seal()  # must not raise
        assert container.conversation.is_sealed

    async def test_delete_clears_scopes_and_calls_deleter(self):
        calls = []

        async def deleter():
            calls.append(True)

        container = TurnStateContainer(
            conversation=TurnState({"a": 1}),
            user=TurnState({"b": 2}),
            _deleter=deleter,
        )
        await container.delete()
        assert container.conversation.is_empty
        assert container.user is not None and container.user.is_empty
        assert calls == [True]


# ---------------------------------------------------------------------------
# TurnStateLoader
# ---------------------------------------------------------------------------


class TestTurnStateLoader:
    def test_requires_a_storage_backend(self):
        with pytest.raises(ValueError):
            TurnStateLoader()

    def test_key_layout_matches_csharp(self):
        loader = TurnStateLoader(LocalStorage())
        assert loader.conversation_key("c1") == "ts:conv:c1"
        assert loader.user_key("c1", "u1") == "ts:user:c1:u1"

    def test_key_prefix_is_configurable(self):
        loader = TurnStateLoader(LocalStorage(), StateOptions(key_prefix="mybot"))
        assert loader.conversation_key("c1") == "mybot:conv:c1"

    async def test_load_missing_returns_empty_scopes(self):
        loader = TurnStateLoader(LocalStorage())
        container = await loader.load("c1", "u1")
        assert container.conversation.is_empty
        assert container.user is not None and container.user.is_empty

    async def test_load_without_user_id_has_no_user_scope(self):
        loader = TurnStateLoader(LocalStorage())
        container = await loader.load("c1")
        assert container.user is None

    async def test_round_trip(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1", "u1")
        container.conversation["greeted"] = True
        assert container.user is not None
        container.user["step"] = 3
        await loader.save(container)

        reloaded = await loader.load("c1", "u1")
        assert reloaded.conversation["greeted"] is True
        assert reloaded.user is not None and reloaded.user["step"] == 3

    async def test_save_persists_json_string(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        container.conversation["k"] = "v"
        await loader.save(container)

        stored = storage.get("ts:conv:c1")
        assert isinstance(stored, str)  # design §13.1: always a str
        parsed = json.loads(stored)
        assert parsed["data"] == {"k": "v"}
        assert "ts" in parsed

    async def test_clean_scope_is_not_written(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        # never mutated -> nothing written
        await loader.save(container)
        assert storage.get("ts:conv:c1") is None

    async def test_emptied_scope_is_deleted(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        # seed an existing blob
        container = await loader.load("c1")
        container.conversation["k"] = "v"
        await loader.save(container)
        assert storage.get("ts:conv:c1") is not None

        # now empty it and save -> key removed
        again = await loader.load("c1")
        del again.conversation["k"]
        await loader.save(again)
        assert storage.get("ts:conv:c1") is None

    async def test_delete_removes_both_keys(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1", "u1")
        container.conversation["a"] = 1
        assert container.user is not None
        container.user["b"] = 2
        await loader.save(container)
        assert storage.get("ts:conv:c1") is not None
        assert storage.get("ts:user:c1:u1") is not None

        await loader.delete("c1", "u1")
        assert storage.get("ts:conv:c1") is None
        assert storage.get("ts:user:c1:u1") is None

    async def test_corrupt_blob_loads_as_empty(self):
        storage = LocalStorage()
        await storage.async_set("ts:conv:c1", "not-json{{{")
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        assert container.conversation.is_empty

    async def test_blob_without_data_loads_as_empty(self):
        storage = LocalStorage()
        await storage.async_set("ts:conv:c1", json.dumps({"ts": time.time()}))
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        assert container.conversation.is_empty

    async def test_expired_blob_loads_as_empty(self):
        storage = LocalStorage()
        await storage.async_set(
            "ts:conv:c1",
            json.dumps({"ts": time.time() - 500, "data": {"a": 1}}),
        )
        loader = TurnStateLoader(storage, StateOptions(ttl=100))
        container = await loader.load("c1")
        assert container.conversation.is_empty

    async def test_unexpired_blob_loads_normally(self):
        storage = LocalStorage()
        await storage.async_set(
            "ts:conv:c1",
            json.dumps({"ts": time.time(), "data": {"a": 1}}),
        )
        loader = TurnStateLoader(storage, StateOptions(ttl=100))
        container = await loader.load("c1")
        assert container.conversation["a"] == 1

    async def test_storage_from_options_is_used(self):
        storage = LocalStorage()
        loader = TurnStateLoader(options=StateOptions(storage=storage))
        container = await loader.load("c1")
        container.conversation["k"] = "v"
        await loader.save(container)
        assert storage.get("ts:conv:c1") is not None
