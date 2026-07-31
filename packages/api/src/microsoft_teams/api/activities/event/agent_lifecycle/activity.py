"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Annotated, Literal, Union

from pydantic import Field

from ....models import ActivityBase, CustomBaseModel
from .value import (
    AgenticUserDeletedValue,
    AgenticUserDisabledValue,
    AgenticUserEnabledValue,
    AgenticUserIdentityCreatedValue,
    AgenticUserIdentityUpdatedValue,
    AgenticUserManagerUpdatedValue,
    AgenticUserUndeletedValue,
    AgenticUserWorkloadOnboardingUpdatedValue,
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


class AgenticUserIdentityCreatedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic user identity is created."""

    value_type: Literal["AgenticUserIdentityCreated"] = "AgenticUserIdentityCreated"
    value: AgenticUserIdentityCreatedValue


class AgenticUserIdentityUpdatedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic user identity property changes."""

    value_type: Literal["AgenticUserIdentityUpdated"] = "AgenticUserIdentityUpdated"
    value: AgenticUserIdentityUpdatedValue


class AgenticUserManagerUpdatedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic user's manager changes."""

    value_type: Literal["AgenticUserManagerUpdated"] = "AgenticUserManagerUpdated"
    value: AgenticUserManagerUpdatedValue


class AgenticUserEnabledActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic user is enabled."""

    value_type: Literal["AgenticUserEnabled"] = "AgenticUserEnabled"
    value: AgenticUserEnabledValue


class AgenticUserDisabledActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic user is disabled."""

    value_type: Literal["AgenticUserDisabled"] = "AgenticUserDisabled"
    value: AgenticUserDisabledValue


class AgenticUserDeletedActivity(AgentLifecycleEventActivityBase):
    """Fired when an agentic user is deleted."""

    value_type: Literal["AgenticUserDeleted"] = "AgenticUserDeleted"
    value: AgenticUserDeletedValue


class AgenticUserUndeletedActivity(AgentLifecycleEventActivityBase):
    """Fired when a previously deleted agentic user is restored."""

    value_type: Literal["AgenticUserUndeleted"] = "AgenticUserUndeleted"
    value: AgenticUserUndeletedValue


class AgenticUserWorkloadOnboardingUpdatedActivity(AgentLifecycleEventActivityBase):
    """Fired when a workload onboarding state changes for an agentic user."""

    value_type: Literal["AgenticUserWorkloadOnboardingUpdated"] = "AgenticUserWorkloadOnboardingUpdated"
    value: AgenticUserWorkloadOnboardingUpdatedValue


AgentLifecycleEventActivity = Annotated[
    Union[
        AgenticUserIdentityCreatedActivity,
        AgenticUserIdentityUpdatedActivity,
        AgenticUserManagerUpdatedActivity,
        AgenticUserEnabledActivity,
        AgenticUserDisabledActivity,
        AgenticUserDeletedActivity,
        AgenticUserUndeletedActivity,
        AgenticUserWorkloadOnboardingUpdatedActivity,
    ],
    Field(discriminator="value_type"),
]
"""Union of all Agent 365 ``agentLifecycle`` event activities, discriminated by ``valueType``."""

__all__ = [
    "AgentLifecycleEventActivityBase",
    "AgenticUserIdentityCreatedActivity",
    "AgenticUserIdentityUpdatedActivity",
    "AgenticUserManagerUpdatedActivity",
    "AgenticUserEnabledActivity",
    "AgenticUserDisabledActivity",
    "AgenticUserDeletedActivity",
    "AgenticUserUndeletedActivity",
    "AgenticUserWorkloadOnboardingUpdatedActivity",
    "AgentLifecycleEventActivity",
]
