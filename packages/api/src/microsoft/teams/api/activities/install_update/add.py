"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal

from ...models import ActivityBase, CustomBaseModel
from ..utils import input_model


class InstalledActivity(ActivityBase, CustomBaseModel):
    type: Literal["installationUpdate"] = "installationUpdate"  # pyright: ignore [reportIncompatibleVariableOverride]

    action: Literal["add"] = "add"
    """Install update action"""


@input_model
class InstalledActivityInput(InstalledActivity):
    """
    Input type for InstalledActivity where ActivityBase fields are optional
    but installationUpdate-specific fields retain their required status.
    """

    pass
