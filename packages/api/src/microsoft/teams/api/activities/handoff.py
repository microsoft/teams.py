"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from abc import ABC
from typing import Literal

from ..models import CustomBaseModel
from .activity import Activity


class HandoffActivity(Activity, CustomBaseModel, ABC):
    type: Literal["handoff"] = "handoff"
