"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import os
import warnings
from typing import Any

from hatchling.version.source.plugin.interface import VersionSourceInterface
from nbgv_python.errors import NbgvError  # type: ignore[import-untyped]
from nbgv_python.hatch_plugin import NbgvVersionSource as _UpstreamSource  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)

_FALLBACK_VERSION = "0.0.0"


class NbgvVersionSource(VersionSourceInterface):
    PLUGIN_NAME = "nbgv"

    def get_version_data(self) -> dict[str, Any]:
        try:
            upstream = _UpstreamSource(self.root, self.config)  # type: ignore[arg-type]
            return upstream.get_version_data()
        except NbgvError:
            if os.environ.get("NBGV_REQUIRED"):
                raise
            warnings.warn(
                "nbgv CLI not found — using fallback version 0.0.0. "
                "Install .NET SDK and nbgv for real versions. "
                "Set NBGV_REQUIRED=1 to make this a hard error.",
                UserWarning,
                stacklevel=1,
            )
            logger.warning("nbgv not found, falling back to version %s", _FALLBACK_VERSION)
            return {"version": _FALLBACK_VERSION}

    def set_version(self, version: str, version_data: dict[str, Any]) -> None:
        raise NotImplementedError("Version is managed by nbgv via version.json — not settable.")
