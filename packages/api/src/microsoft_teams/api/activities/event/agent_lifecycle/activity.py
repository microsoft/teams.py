"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Literal, Union

from pydantic import Field

from ....models import ActivityBase, CustomBaseModel
from .value import (
    AgenticIdentityCreatedValue,
    AgenticIdentityDeletedValue,
    AgenticIdentityDisabledValue,
    AgenticIdentityEnabledValue,
    AgenticIdentityManagerUpdatedValue,
    AgenticIdentityUndeletedValue,
    AgenticIdentityUpdatedValue,
    AgenticIdentityWorkloadOnboardingUpdatedValue,
)


class AgentLifecycleEventActivityBase(ActivityBase, CustomBaseModel):
    """Base for Agent 365 ``agentLifecycle`` event activities.

    These activities arrive from the ``System`` user on the ``agents`` channel with
    ``type == "event"`` and ``name == "agentLifecycle"``. The ``value_type`` field
    names the variant and ``value`` carries the typed payload.
    """

    type: Literal["event"] = "event"

    name: Literal["agentLifecycle"] = "agentLifecycle"
    """The name of the operation associated with an event activity."""


class AgenticIdentityCreatedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic identity is created."""

    value_type: Literal["AgenticUserIdentityCreated"] = "AgenticUserIdentityCreated"
    value: AgenticIdentityCreatedValue


class AgenticIdentityUpdatedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic identity property changes."""

    value_type: Literal["AgenticUserIdentityUpdated"] = "AgenticUserIdentityUpdated"
    value: AgenticIdentityUpdatedValue


class AgenticIdentityManagerUpdatedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic identity's manager changes."""

    value_type: Literal["AgenticUserManagerUpdated"] = "AgenticUserManagerUpdated"
    value: AgenticIdentityManagerUpdatedValue


class AgenticIdentityEnabledActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic identity is enabled."""

    value_type: Literal["AgenticUserEnabled"] = "AgenticUserEnabled"
    value: AgenticIdentityEnabledValue


class AgenticIdentityDisabledActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic identity is disabled."""

    value_type: Literal["AgenticUserDisabled"] = "AgenticUserDisabled"
    value: AgenticIdentityDisabledValue


class AgenticIdentityDeletedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic identity is deleted."""

    value_type: Literal["AgenticUserDeleted"] = "AgenticUserDeleted"
    value: AgenticIdentityDeletedValue


class AgenticIdentityUndeletedActivity(AgentLifecycleEventActivityBase):
    """Fired when a previously deleted agentic identity is restored."""

    value_type: Literal["AgenticUserUndeleted"] = "AgenticUserUndeleted"
    value: AgenticIdentityUndeletedValue


class AgenticIdentityWorkloadOnboardingUpdatedActivity(AgentLifecycleEventActivityBase):
    """Fired when a workload onboarding state changes for an agentic identity."""

    value_type: Literal["AgenticUserWorkloadOnboardingUpdated"] = "AgenticUserWorkloadOnboardingUpdated"
    value: AgenticIdentityWorkloadOnboardingUpdatedValue


AgentLifecycleEventActivity = Annotated[
    Union[
        AgenticIdentityCreatedActivity,
        AgenticIdentityUpdatedActivity,
        AgenticIdentityManagerUpdatedActivity,
        AgenticIdentityEnabledActivity,
        AgenticIdentityDisabledActivity,
        AgenticIdentityDeletedActivity,
        AgenticIdentityUndeletedActivity,
        AgenticIdentityWorkloadOnboardingUpdatedActivity,
    ],
    Field(discriminator="value_type"),
]
"""Union of all Agent 365 ``agentLifecycle`` event activities, discriminated by ``valueType``."""

__all__ = [
    "AgentLifecycleEventActivityBase",
    "AgenticIdentityCreatedActivity",
    "AgenticIdentityUpdatedActivity",
    "AgenticIdentityManagerUpdatedActivity",
    "AgenticIdentityEnabledActivity",
    "AgenticIdentityDisabledActivity",
    "AgenticIdentityDeletedActivity",
    "AgenticIdentityUndeletedActivity",
    "AgenticIdentityWorkloadOnboardingUpdatedActivity",
    "AgentLifecycleEventActivity",
]
