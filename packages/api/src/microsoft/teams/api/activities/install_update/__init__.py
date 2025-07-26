"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .add import InstalledActivity
from .remove import UninstalledActivity

InstallUpdateActivity = Annotated[Union[InstalledActivity, UninstalledActivity], Field(discriminator="action")]

__all__ = [
    "InstalledActivity",
    "UninstalledActivity",
    "InstallUpdateActivity",
]
