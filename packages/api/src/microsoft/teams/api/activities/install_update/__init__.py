"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Union

from .add import InstalledActivity
from .remove import UninstalledActivity

InstallUpdateActivity = Union[InstalledActivity, UninstalledActivity]

__all__ = [
    "InstalledActivity",
    "UninstalledActivity",
    "InstallUpdateActivity",
]
