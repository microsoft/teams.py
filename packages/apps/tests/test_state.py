"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
from typing import Any
from unittest.mock import MagicMock

import pytest
from microsoft_teams.apps.state import (
    StateOptions,
    TurnState,
    TurnStateContainer,
    TurnStateLoader,
    TurnStateSealedError,
    create_state_loader,
)
from microsoft_teams.common import LocalStorage, Storage

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

    def test_nested_dict_mutation_marks_dirty(self):
        state = TurnState({"oauth": {"github": {"pending": False}}})
        state["oauth"]["github"]["pending"] = True
        assert state.is_dirty is True

    def test_nested_list_mutation_marks_dirty(self):
        state = TurnState({"items": [1, 2]})
        state["items"].append(3)
        assert state.is_dirty is True

    def test_mutate_then_revert_is_clean(self):
        state = TurnState({"x": 1})
        state["x"] = 2
        assert state.is_dirty is True
        state["x"] = 1
        assert state.is_dirty is False

    def test_circular_value_is_dirty_without_raising(self):
        state = TurnState()
        value: dict[str, object] = {}
        value["self"] = value

        state["value"] = value

        assert state.is_dirty is True

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
        container = TurnStateContainer(conversation=TurnState(), conversation_id="c1", user=TurnState())
        container.seal()
        assert container.conversation.is_sealed
        assert container.user is not None and container.user.is_sealed

    def test_seal_tolerates_missing_user(self):
        container = TurnStateContainer(conversation=TurnState(), conversation_id="c1", user=None)
        container.seal()  # must not raise
        assert container.conversation.is_sealed

    async def test_delete_clears_scopes_and_calls_deleter(self):
        calls = []

        async def deleter():
            calls.append(True)

        container = TurnStateContainer(
            conversation=TurnState({"a": 1}),
            conversation_id="c1",
            user=TurnState({"b": 2}),
            _deleter=deleter,
        )
        await container.delete()
        assert container.conversation.is_empty
        assert container.conversation.is_dirty is False
        assert container.user is not None and container.user.is_empty
        assert container.user.is_dirty is False
        assert calls == [True]

    async def test_delete_without_deleter_raises(self):
        container = TurnStateContainer(
            conversation=TurnState({"a": 1}),
            conversation_id="c1",
            user=TurnState({"b": 2}),
        )

        with pytest.raises(RuntimeError, match="State deletion is not available"):
            await container.delete()

        assert container.conversation["a"] == 1
        assert container.user is not None and container.user["b"] == 2


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

    def test_key_segments_are_escaped(self):
        loader = TurnStateLoader(LocalStorage())
        assert loader.conversation_key("c:1;tenant=a") == "ts:conv:c%3A1%3Btenant%3Da"
        assert loader.user_key("c:1", "u;1=a/b") == "ts:user:c%3A1:u%3B1%3Da%2Fb"

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

    async def test_save_marks_saved_scopes_clean(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1", "u1")
        container.conversation["saved"] = True
        assert container.user is not None
        container.user["saved"] = True

        await loader.save(container)

        assert container.conversation.is_dirty is False
        assert container.user.is_dirty is False

    async def test_save_surfaces_circular_value_during_serialization(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        value: dict[str, object] = {}
        value["self"] = value
        container.conversation["value"] = value

        with pytest.raises(ValueError):
            await loader.save(container)

        assert storage.get("ts:conv:c1") is None
        assert container.conversation.is_dirty is True

    async def test_nested_mutation_persists(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        container.conversation["oauth"] = {"github": {"pending": False}}
        await loader.save(container)

        again = await loader.load("c1")
        again.conversation["oauth"]["github"]["pending"] = True
        await loader.save(again)

        reloaded = await loader.load("c1")
        assert reloaded.conversation["oauth"]["github"]["pending"] is True

    async def test_save_persists_json_string(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        container.conversation["k"] = "v"
        await loader.save(container)

        stored = storage.get("ts:conv:c1")
        assert isinstance(stored, str)  # design §13.1: always a str
        parsed = json.loads(stored)
        assert parsed == {"k": "v"}

    async def test_clean_scope_is_not_written(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        # never mutated -> nothing written
        await loader.save(container)
        assert storage.get("ts:conv:c1") is None

    async def test_save_serializes_all_scopes_before_writing(self):
        storage = LocalStorage()
        loader = TurnStateLoader(storage)
        container = await loader.load("c1", "u1")
        container.conversation["value"] = "old"
        assert container.user is not None
        container.user["value"] = "old"
        await loader.save(container)

        again = await loader.load("c1", "u1")
        again.conversation["value"] = "new"
        assert again.user is not None
        again.user["bad"] = object()

        with pytest.raises(TypeError):
            await loader.save(again)

        reloaded = await loader.load("c1", "u1")
        assert reloaded.conversation["value"] == "old"
        assert reloaded.user is not None and reloaded.user["value"] == "old"

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
        assert storage.get("ts:conv:c1") is None

    async def test_non_mapping_blob_loads_as_empty_and_is_deleted(self):
        storage = LocalStorage()
        await storage.async_set("ts:conv:c1", json.dumps(["not", "state"]))
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        assert container.conversation.is_empty
        assert storage.get("ts:conv:c1") is None

    async def test_already_deserialized_dict_loads_normally(self):
        storage: LocalStorage[Any] = LocalStorage()
        await storage.async_set("ts:conv:c1", {"a": 1})
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        assert container.conversation["a"] == 1

    async def test_dict_with_non_string_key_is_deleted(self):
        storage: LocalStorage[Any] = LocalStorage()
        await storage.async_set("ts:conv:c1", {1: "not state"})
        loader = TurnStateLoader(storage)
        container = await loader.load("c1")
        assert container.conversation.is_empty
        assert storage.get("ts:conv:c1") is None

    async def test_storage_from_options_is_used(self):
        storage = LocalStorage()
        loader = TurnStateLoader(options=StateOptions(storage=storage))
        container = await loader.load("c1")
        container.conversation["k"] = "v"
        await loader.save(container)
        assert storage.get("ts:conv:c1") is not None


# ---------------------------------------------------------------------------
# create_state_loader (App(state=...) resolution)
# ---------------------------------------------------------------------------


class TestCreateStateLoader:
    def test_returns_none_when_disabled(self):
        assert create_state_loader(None, LocalStorage()) is None
        assert create_state_loader(False, LocalStorage()) is None

    def test_true_enables_on_fallback_storage_and_warns(self, caplog):
        fallback = LocalStorage()
        with caplog.at_level(logging.WARNING):
            loader = create_state_loader(True, fallback)
        assert isinstance(loader, TurnStateLoader)
        assert any("localstorage" in r.message.lower() for r in caplog.records)

    async def test_options_storage_is_used_over_fallback(self):
        dedicated: LocalStorage[str] = LocalStorage()
        fallback: LocalStorage[str] = LocalStorage()
        loader = create_state_loader(StateOptions(storage=dedicated), fallback)
        assert loader is not None

        container = await loader.load("c1")
        container.conversation["k"] = "v"
        await loader.save(container)

        assert dedicated.get("ts:conv:c1") is not None
        assert fallback.get("ts:conv:c1") is None

    def test_non_local_storage_does_not_warn(self, caplog):
        fake_storage = MagicMock(spec=Storage)
        with caplog.at_level(logging.WARNING):
            loader = create_state_loader(StateOptions(storage=fake_storage), LocalStorage())
        assert isinstance(loader, TurnStateLoader)
        assert not any("localstorage" in r.message.lower() for r in caplog.records)
