"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from ..custom_base_model import CustomBaseModel
from .entity_base import EntityBase

PlanType = Literal["start", "continue", "complete", "stop", "error"]
StepStatus = Literal["active", "proposed", "completed", "blocked", "error"]


class StepSource(CustomBaseModel):
    title: str
    url: str
    icon: Optional[str] = None


class Step(CustomBaseModel):
    id: str
    version: int
    title: str
    status: StepStatus
    description: Optional[str] = None
    sources: Optional[list[StepSource]] = None


class PlanInfoEntity(EntityBase):
    type: Literal["planInfo"] = "planInfo"
    plan_type: PlanType
    steps: Optional[list[Step]] = None
