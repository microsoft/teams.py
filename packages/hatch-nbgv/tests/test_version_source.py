"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from unittest.mock import patch

import pytest
from hatch_nbgv.version_source import NbgvVersionSource
from nbgv_python.errors import NbgvNotFoundError  # type: ignore[import-untyped]


def _make_source(config: dict[str, object] | None = None) -> NbgvVersionSource:
    return NbgvVersionSource("/tmp", config or {})


class TestGetVersionData:
    def test_delegates_to_upstream(self):
        source = _make_source()
        fake_data: dict[str, object] = {"version": "2.0.0a31"}
        with patch("hatch_nbgv.version_source._UpstreamSource") as mock_cls:
            mock_cls.return_value.get_version_data.return_value = fake_data
            result = source.get_version_data()
            assert result == fake_data

    def test_fallback_when_nbgv_not_found(self):
        source = _make_source()
        with patch("hatch_nbgv.version_source._UpstreamSource") as mock_cls:
            mock_cls.return_value.get_version_data.side_effect = NbgvNotFoundError()
            result = source.get_version_data()
            assert result == {"version": "0.0.0"}

    def test_hard_fail_when_nbgv_required(self):
        source = _make_source()
        with patch("hatch_nbgv.version_source._UpstreamSource") as mock_cls:
            mock_cls.return_value.get_version_data.side_effect = NbgvNotFoundError()
            with patch.dict("os.environ", {"NBGV_REQUIRED": "1"}):
                with pytest.raises(NbgvNotFoundError):
                    source.get_version_data()


class TestSetVersion:
    def test_set_version_raises(self):
        source = _make_source()
        with pytest.raises(NotImplementedError):
            source.set_version("1.0.0", {})
