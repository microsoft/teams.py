"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import asyncio
import warnings

from microsoft_teams.common.experimental import ExperimentalWarning, experimental


@experimental("TEST001")
class _PreviewClass:
    def __init__(self, value: str):
        self.value = value


@experimental("TEST002")
def _preview_sync_func(x: int) -> int:
    return x * 2


@experimental("TEST003")
async def _preview_async_func(x: int) -> int:
    return x * 3


class TestExperimentalWarning:
    def test_class_instantiation_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            obj = _PreviewClass("test")
            assert len(w) == 1
            assert issubclass(w[0].category, ExperimentalWarning)
            assert "TEST001" in str(w[0].message)
            assert "preview" in str(w[0].message).lower()
            assert obj.value == "test"

    def test_sync_function_emits_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = _preview_sync_func(5)
            assert len(w) == 1
            assert issubclass(w[0].category, ExperimentalWarning)
            assert "TEST002" in str(w[0].message)
            assert result == 10

    def test_async_function_emits_warning(self):
        async def _run() -> int:
            return await _preview_async_func(5)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = asyncio.run(_run())
            assert len(w) == 1
            assert issubclass(w[0].category, ExperimentalWarning)
            assert "TEST003" in str(w[0].message)
            assert result == 15

    def test_warning_is_suppressible(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings("ignore", category=ExperimentalWarning)
            _PreviewClass("suppressed")
            assert len(w) == 0

    def test_warning_is_suppressible_by_message(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.filterwarnings("ignore", message=".*TEST001.*", category=ExperimentalWarning)
            _PreviewClass("suppressed")
            result = _preview_sync_func(5)
            assert len(w) == 1  # only TEST002 warning, not TEST001
            assert "TEST002" in str(w[0].message)
            assert result == 10

    def test_custom_message(self):
        @experimental("CUSTOM", message="Custom preview message.")
        def custom_func() -> str:
            return "ok"

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = custom_func()
            assert len(w) == 1
            assert str(w[0].message) == "Custom preview message."
            assert result == "ok"

    def test_warning_is_future_warning_subclass(self):
        assert issubclass(ExperimentalWarning, FutureWarning)
