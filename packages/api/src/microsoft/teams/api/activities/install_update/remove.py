"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ActivityBase, CustomBaseModel


class UninstalledActivity(ActivityBase, CustomBaseModel):
    type: Literal["installationUpdate"] = "installationUpdate"  #

    action: Literal["remove"] = "remove"
    """Uninstall update action"""
