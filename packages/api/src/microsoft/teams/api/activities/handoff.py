"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Literal

from ..models import ActivityBase, CustomBaseModel
from .utils import input_model


class HandoffActivity(ActivityBase, CustomBaseModel, ABC):
    type: Literal["handoff"] = "handoff"  # pyright: ignore [reportIncompatibleVariableOverride]


@input_model
class HandoffActivityInput(HandoffActivity):
    """
    Input type for HandoffActivity where ActivityBase fields are optional
    but handoff-specific fields retain their required status.
    """

    pass
