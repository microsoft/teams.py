"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Union

from pydantic import Field

from .add import InstalledActivity, InstalledActivityInput
from .remove import UninstalledActivity, UninstalledActivityInput

InstallUpdateActivity = Annotated[Union[InstalledActivity, UninstalledActivity], Field(discriminator="action")]
InstallUpdateActivityInput = Annotated[
    Union[InstalledActivityInput, UninstalledActivityInput], Field(discriminator="action")
]

__all__ = [
    "InstalledActivity",
    "InstalledActivityInput",
    "UninstalledActivity",
    "UninstalledActivityInput",
    "InstallUpdateActivity",
    "InstallUpdateActivityInput",
]
