"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from .local_storage import LocalStorage, LocalStorageOptions


def test_get_undefined():
    storage = LocalStorage()
    assert storage.get("test") is None


def test_set_get_delete():
    storage = LocalStorage()
    storage.set("testing", "123")
    assert storage.get("testing") == "123"
    storage.delete("testing")
    assert storage.get("testing") is None


def test_max_size():
    storage = LocalStorage(options=LocalStorageOptions(max=3))

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
