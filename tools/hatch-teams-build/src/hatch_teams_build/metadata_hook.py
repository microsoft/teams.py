"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

import logging
import os
import re
from typing import Any

from hatchling.metadata.plugin.interface import MetadataHookInterface

from hatch_teams_build.version_source import FALLBACK_VERSION, TeamsBuildVersionSource

logger = logging.getLogger(__name__)

_WORKSPACE_PREFIX = "microsoft-teams-"

# Matches a bare package name with no version specifier (e.g. "microsoft-teams-common")
# but not one that already has a constraint (e.g. "microsoft-teams-common>=1.0")
_BARE_DEP_RE = re.compile(r"^([a-zA-Z0-9_-]+)$")


def _strip_local(version: str) -> str:
    """Strip PEP 440 local segment (e.g. +gf235eb85) since it's not allowed in dependency specifiers."""
    return version.split("+")[0]


def _add_version_constraint(dep: str, version: str) -> str:
    """Add >={version} to a bare microsoft-teams-* dependency."""
    match = _BARE_DEP_RE.match(dep.strip())
    if match and match.group(1).startswith(_WORKSPACE_PREFIX):
        return f"{match.group(1)}>={version}"
    return dep


class TeamsBuildMetadataHook(MetadataHookInterface):
    PLUGIN_NAME = "teams-build"

    def update(self, metadata: dict[str, Any]) -> None:
        source = TeamsBuildVersionSource(self.root, self.config)
        version = _strip_local(source.get_version_data()["version"])

        fallback = _strip_local(FALLBACK_VERSION)
        if version == fallback:
            if os.environ.get("NBGV_REQUIRED"):
                raise RuntimeError(
                    f"teams-build metadata hook: nbgv resolved to {fallback} but NBGV_REQUIRED is set. "
                    "Workspace dependency versions would be incorrect. "
                    "Ensure nbgv CLI is installed and available on PATH."
                )
            logger.warning(
                "teams-build metadata hook: skipping dep rewrite (nbgv unavailable, version is %s)", fallback
            )
            return

        logger.debug("teams-build metadata hook: rewriting workspace deps with >=%s", version)

        if "dependencies" in metadata:
            metadata["dependencies"] = [_add_version_constraint(dep, version) for dep in metadata["dependencies"]]

        if "optional-dependencies" in metadata:
            for extra, deps in metadata["optional-dependencies"].items():
                metadata["optional-dependencies"][extra] = [_add_version_constraint(dep, version) for dep in deps]
