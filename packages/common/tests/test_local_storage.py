"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import pytest
from microsoft_teams.common.storage import ListLocalStorage, LocalStorage, LocalStorageOptions, StorageOptions


def test_get_undefined() -> None:
    storage: LocalStorage[int] = LocalStorage()
    assert storage.get("test") is None


def test_set_get_delete() -> None:
    storage: LocalStorage[str] = LocalStorage()
    storage.set("testing", "123")
    assert storage.get("testing") == "123"
    storage.delete("testing")
    assert storage.get("testing") is None


def test_max_size() -> None:
    storage: LocalStorage[int] = LocalStorage(options=LocalStorageOptions(max=3))

    storage.set("a", 1)
    storage.set("b", 2)
    storage.set("c", 3)

    assert storage.get("a") == 1
    assert storage.get("b") == 2
    assert storage.get("c") == 3
    assert storage.keys == ["a", "b", "c"]
    assert storage.size == 3

    storage.set("d", 4)

    assert storage.get("a") is None
    assert storage.get("b") == 2
    assert storage.get("c") == 3
    assert storage.get("d") == 4
    assert storage.keys == ["b", "c", "d"]
    assert storage.size == 3


async def test_inherited_options_write_preserves_existing_storage_implementations() -> None:
    storage = ListLocalStorage[int]([1])

    storage.set_with_options(0, 2, StorageOptions())
    await storage.async_set_with_options(0, 3, StorageOptions())

    assert storage.get(0) == 3
    with pytest.raises(NotImplementedError, match="does not support TTL"):
        await storage.async_set_with_options(0, 4, StorageOptions(ttl=10))


def test_ttl_expiry_removes_value_from_all_surfaces(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr("microsoft_teams.common.storage.local_storage.monotonic", lambda: now[0])
    storage = LocalStorage[str]()

    storage.set_with_options("key", "value", StorageOptions(ttl=10))
    assert storage.get("key") == "value"

    now[0] = 110.0

    assert storage.keys == []
    assert storage.size == 0
    assert dict(storage.store) == {}
    assert storage.get("key") is None


def test_regular_set_replaces_value_and_clears_ttl(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr("microsoft_teams.common.storage.local_storage.monotonic", lambda: now[0])
    storage = LocalStorage[str]()

    storage.set_with_options("key", "expiring", StorageOptions(ttl=10))
    storage.set("key", "persistent")
    now[0] = 111.0

    assert storage.get("key") == "persistent"


def test_delete_clears_ttl_metadata(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr("microsoft_teams.common.storage.local_storage.monotonic", lambda: now[0])
    storage = LocalStorage[str]()

    storage.set_with_options("key", "expiring", StorageOptions(ttl=10))
    storage.delete("key")
    storage.set("key", "replacement")
    now[0] = 111.0

    assert storage.get("key") == "replacement"


def test_expired_values_do_not_evict_live_values_at_capacity(monkeypatch) -> None:
    now = [100.0]
    monkeypatch.setattr("microsoft_teams.common.storage.local_storage.monotonic", lambda: now[0])
    storage = LocalStorage[int](options=LocalStorageOptions(max=2))

    storage.set_with_options("expired", 1, StorageOptions(ttl=10))
    storage.set("live", 2)
    assert storage.get("expired") == 1

    now[0] = 111.0
    storage.set("new", 3)

    assert storage.get("expired") is None
    assert storage.get("live") == 2
    assert storage.get("new") == 3
