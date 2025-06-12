"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from common.storage import ListLocalStorage


def test_get_undefined_empty_index() -> None:
    storage: ListLocalStorage[int] = ListLocalStorage()
    assert storage.get(0) is None


def test_push_and_get() -> None:
    storage = ListLocalStorage[int]()
    storage.append(1)
    storage.append(2)
    assert storage.get(0) == 1
    assert storage.get(1) == 2
    assert storage.length() == 2


def test_set_and_overwrite() -> None:
    storage = ListLocalStorage[int]([1, 2, 3])
    storage.set(1, 42)
    assert storage.get(1) == 42
    assert storage.items() == [1, 42, 3]


def test_delete_by_index() -> None:
    storage = ListLocalStorage[int]([1, 2, 3])
    storage.delete(1)
    assert storage.items() == [1, 3]
    assert storage.length() == 2


def test_pop() -> None:
    storage = ListLocalStorage[int]([1, 2, 3])
    assert storage.pop() == 3
    assert storage.items() == [1, 2]
    assert storage.length() == 2


def test_get_all_values() -> None:
    storage = ListLocalStorage[int]([1, 2, 3])
    assert storage.items() == [1, 2, 3]


def test_filter_with_where() -> None:
    storage = ListLocalStorage[int]([1, 2, 3, 4])
    even = storage.filter(lambda v, i: v % 2 == 0)
    assert even == [2, 4]


def test_mixed_operations() -> None:
    storage = ListLocalStorage[str]()
    storage.append("a")
    storage.append("b")
    storage.append("c")
    assert storage.items() == ["a", "b", "c"]
    storage.set(1, "B")
    assert storage.get(1) == "B"
    storage.delete(0)
    assert storage.items() == ["B", "c"]
    storage.pop()
    assert storage.items() == ["B"]
    assert storage.length() == 1
