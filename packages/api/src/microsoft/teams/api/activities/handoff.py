"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Literal

from ..models import ActivityBase, CustomBaseModel


class HandoffActivity(ActivityBase, CustomBaseModel, ABC):
    type: Literal["handoff"] = "handoff"  # pyright: ignore [reportIncompatibleVariableOverride]
