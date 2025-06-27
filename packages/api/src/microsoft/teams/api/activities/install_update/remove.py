"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import CustomBaseModel
from ..activity import Activity


class UninstalledActivity(Activity, CustomBaseModel):
    _type: Literal["installationUpdate"] = "installationUpdate"

    @property
    def type(self) -> str:
        """The type of the activity."""
        return self._type

    action: Literal["remove"] = "remove"
    """Uninstall update action"""
