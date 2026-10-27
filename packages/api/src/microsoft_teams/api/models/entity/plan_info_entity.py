"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel
from .entity_base import EntityBase

PlanType = Literal["start", "continue", "complete", "stop", "error"]
StepStatus = Literal["active", "proposed", "completed", "blocked", "error"]


@experimental("ExperimentalTeamsPlan")
class StepSource(CustomBaseModel):
    title: str
    url: str
    icon: Optional[str] = None


@experimental("ExperimentalTeamsPlan")
class Step(CustomBaseModel):
    id: str
    version: int
    title: str
    status: StepStatus
    description: Optional[str] = None
    sources: Optional[list[StepSource]] = None


@experimental("ExperimentalTeamsPlan")
class PlanInfoEntity(EntityBase):
    type: Literal["planInfo"] = "planInfo"
    plan_type: PlanType
    steps: Optional[list[Step]] = None
