"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from hatchling.plugin import hookimpl

from hatch_nbgv.version_source import NbgvVersionSource


@hookimpl
def hatch_register_version_source():
    return NbgvVersionSource
