"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import json
import logging
import os
import subprocess
import warnings
from typing import Any

from hatchling.version.source.plugin.interface import VersionSourceInterface
from packaging.version import Version

logger = logging.getLogger(__name__)

FALLBACK_VERSION = "0.0.0"
_VERSION_FIELD_NAMES = ("CloudBuildNumber", "AssemblyInformationalVersion", "Version")


def _normalize_version(version: str) -> str:
    return str(Version(version))


def _get_nbgv_version(root: str) -> dict[str, Any]:
    result = subprocess.run(
        ["nbgv", "get-version", "--format", "json", "--project", root],
        check=True,
        capture_output=True,
        cwd=root,
        text=True,
    )
    return json.loads(result.stdout)


def _select_version(version_data: dict[str, Any]) -> str:
    for field_name in _VERSION_FIELD_NAMES:
        value = version_data.get(field_name)
        if isinstance(value, str) and value:
            return value

    raise RuntimeError("nbgv did not return a usable version field")


class TeamsBuildVersionSource(VersionSourceInterface):
    PLUGIN_NAME = "teams-build"

    def get_version_data(self) -> dict[str, Any]:
        try:
            metadata = _get_nbgv_version(self.root)
            version = _normalize_version(_select_version(metadata))
            return {"version": version, "metadata": metadata}
        except (FileNotFoundError, json.JSONDecodeError, subprocess.CalledProcessError, RuntimeError):
            if os.environ.get("NBGV_REQUIRED"):
                raise
            warnings.warn(
                "nbgv CLI not found or failed — using fallback version 0.0.0. "
                "Install .NET SDK and nbgv for real versions. "
                "Set NBGV_REQUIRED=1 to make this a hard error.",
                UserWarning,
                stacklevel=1,
            )
            logger.warning("nbgv unavailable, falling back to version %s", FALLBACK_VERSION)
            return {"version": FALLBACK_VERSION}

    def set_version(self, version: str, version_data: dict[str, Any]) -> None:
        raise NotImplementedError("Version is managed by nbgv via version.json — not settable.")
