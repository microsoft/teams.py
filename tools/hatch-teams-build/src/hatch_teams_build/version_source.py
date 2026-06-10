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
from packaging.version import InvalidVersion, Version

logger = logging.getLogger(__name__)

FALLBACK_VERSION = "0.0.0"
# Field priority for picking a PEP 440-compatible version from nbgv's output.
#   - SemVer2 is the right choice on release ("2.0.13"). On non-release branches it
#     emits the commit hash as an extra prerelease segment (e.g. "2.0.13-dev.11.geaec265930"),
#     which is not PEP 440-valid, so we fall through.
#   - CloudBuildNumber is the fallback for dev/non-release builds where nbgv emits
#     "2.0.13-dev.11+eaec265930" (PEP 440-valid — the "+eaec265930" is a local
#     version segment). Avoid as a primary on release — it would give "2.0.13.4"
#     because nbgv appends git height as a 4th component.
#   - SimpleVersion is the final fallback (loses dev info but always parses).
_VERSION_FIELD_NAMES = ("SemVer2", "CloudBuildNumber", "SimpleVersion")


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
        if not isinstance(value, str) or not value:
            continue
        try:
            Version(value)
        except InvalidVersion:
            logger.debug("nbgv field %s value %r is not PEP 440-compatible, trying next", field_name, value)
            continue
        return value

    raise RuntimeError("nbgv did not return a PEP 440-compatible version in any expected field")


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
