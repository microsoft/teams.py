"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Literal, Optional

from microsoft_teams.api.models.entity.citation_entity import CitationIconName
from microsoft_teams.common.experimental import experimental

from ..custom_base_model import CustomBaseModel
from .entity_base import EntityBase

PlanType = Literal["start", "continue", "complete", "stop", "error"]
StepStatus = Literal["active", "proposed", "completed", "blocked", "error"]


@experimental("ExperimentalTeamsPlan")
class StepSource(CustomBaseModel):
    """A reference source associated with a Plan step."""

    title: str
    """Display title of the source."""

    url: str
    """URL of the source."""

    icon: Optional[CitationIconName] = None
    """Optional icon used to represent the source."""


@experimental("ExperimentalTeamsPlan")
class Step(CustomBaseModel):
    """A versioned step describing work in a Plan.

    Keep the same ``id`` when updating a step and increment ``version`` for
    every change, including changes to its status, title, description, or sources.
    The application is responsible for incrementing the version.
    """

    id: str
    """Stable identifier for the step within the Plan."""

    version: int
    """Step revision number. Increment for every update to the same step."""

    title: str
    """Display title of the step."""

    status: StepStatus
    """Current state of the step: active, proposed, completed, blocked, or error."""

    description: Optional[str] = None
    """Optional details describing the step's work or current state."""

    sources: Optional[list[StepSource]] = None
    """Optional reference sources associated with the step."""


@experimental("ExperimentalTeamsPlan")
class PlanInfoEntity(EntityBase):
    """Activity entity carrying a Plan lifecycle operation and optional steps.

    ``start`` begins a Plan, ``continue`` adds or updates steps, and ``complete``,
    ``stop``, and ``error`` signal the corresponding terminal state.
    """

    type: Literal["planInfo"] = "planInfo"
    """Type identifier for a Plan information entity."""

    plan_type: PlanType
    """Plan lifecycle operation to send."""

    steps: Optional[list[Step]] = None
    """Optional steps for the operation; updated steps must increment their version."""
