"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ActivityBase, CustomBaseModel


class InstalledUpgradeActivity(ActivityBase, CustomBaseModel):
    type: Literal["installationUpdate"] = "installationUpdate"  #

    action: Literal["upgrade"] = "upgrade"
    """Install update action"""
