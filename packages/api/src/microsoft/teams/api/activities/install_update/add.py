"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import CustomBaseModel
from ..activity import Activity


class InstalledActivity(Activity, CustomBaseModel):
    type: Literal["installationUpdate"] = "installationUpdate"

    action: Literal["add"] = "add"
    """Install update action"""
