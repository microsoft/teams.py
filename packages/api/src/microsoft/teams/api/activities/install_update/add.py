"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import CustomBaseModel
from ..activity import IActivity


class InstalledActivity(IActivity[Literal["installationUpdate"]], CustomBaseModel):
    action: Literal["add"] = "add"
    """Install update action"""
