"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ActivityBase, CustomBaseModel
from ..utils import input_model


class UninstalledActivity(ActivityBase, CustomBaseModel):
    type: Literal["installationUpdate"] = "installationUpdate"  # pyright: ignore [reportIncompatibleVariableOverride]

    action: Literal["remove"] = "remove"
    """Uninstall update action"""


@input_model
class UninstalledActivityInput(UninstalledActivity):
    """
    Input type for UninstalledActivity where ActivityBase fields are optional
    but installationUpdate-specific fields retain their required status.
    """

    pass
