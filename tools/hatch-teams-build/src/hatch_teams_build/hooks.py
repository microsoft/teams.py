"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from hatchling.plugin import hookimpl

from hatch_teams_build.metadata_hook import TeamsBuildMetadataHook
from hatch_teams_build.version_source import TeamsBuildVersionSource


@hookimpl
def hatch_register_version_source():
    return TeamsBuildVersionSource


@hookimpl
def hatch_register_metadata_hook():
    return TeamsBuildMetadataHook
