"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import Field

from ....models import CustomBaseModel


class AgentLifecycleManager(CustomBaseModel):
    """Manager profile carried by the ``AgenticUserIdentityCreated`` event."""

    user_id: Optional[str] = None
    """The Entra object ID of the manager."""

    email: Optional[str] = None
    """The manager's email address."""

    display_name: Optional[str] = None
    """The manager's display name."""


class AgentLifecycleManagerRef(CustomBaseModel):
    """Manager reference carried by the ``AgenticUserManagerUpdated`` event."""

    manager_id: Optional[str] = None
    """The Entra object ID of the manager."""


class AgentLifecycleUpdatedProperty(CustomBaseModel):
    """A single property change carried by the ``AgenticUserIdentityUpdated`` event."""

    property_name: str
    """The name of the property that changed (e.g. ``Mail``, ``Alias``, ``UserPrincipalName``)."""

    property_value: Optional[str] = None
    """The new value of the property."""


class AgentLifecycleValueBase(CustomBaseModel):
    """Fields shared by every agentLifecycle event payload."""

    tenant_id: Optional[str] = None
    """The tenant the agentic user belongs to."""

    agentic_user_id: Optional[str] = Field(
        default=None,
        validation_alias="agenticUserId",
        serialization_alias="agenticUserId",
    )
    """The Agent ID user-shaped identity object ID."""

    agentic_app_instance_id: Optional[str] = Field(
        default=None,
        validation_alias="agenticAppInstanceId",
        serialization_alias="agenticAppInstanceId",
    )
    """The concrete agent app instance ID."""

    agentic_blueprint_id: Optional[str] = Field(
        default=None,
        validation_alias="agentIdentityBlueprintId",
        serialization_alias="agentIdentityBlueprintId",
    )
    """The AgenticBlueprint app ID."""

    version: Optional[int] = None
    """Monotonic version of the agentic user state, when provided by the service."""


class AgenticUserIdentityCreatedValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserIdentityCreated`` event."""

    event_type: Literal["agenticUserIdentityCreated"] = "agenticUserIdentityCreated"

    manager: Optional[AgentLifecycleManager] = None
    """The manager assigned to the agentic user at creation."""

    expiration_date_time: Optional[datetime] = None
    """When the agentic user identity expires."""


class AgenticUserIdentityUpdatedValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserIdentityUpdated`` event."""

    event_type: Literal["agenticUserIdentityUpdated"] = "agenticUserIdentityUpdated"

    updated_property: AgentLifecycleUpdatedProperty
    """The property that changed."""


class AgenticUserManagerUpdatedValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserManagerUpdated`` event."""

    event_type: Literal["agenticUserManagerUpdated"] = "agenticUserManagerUpdated"

    manager: Optional[AgentLifecycleManagerRef] = None
    """The new manager reference. Absent when the manager was removed."""


class AgenticUserEnabledValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserEnabled`` event."""

    event_type: Literal["agenticUserEnabled"] = "agenticUserEnabled"


class AgenticUserDisabledValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserDisabled`` event."""

    event_type: Literal["agenticUserDisabled"] = "agenticUserDisabled"


class AgenticUserDeletedValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserDeleted`` event."""

    event_type: Literal["agenticUserDeleted"] = "agenticUserDeleted"

    deletion_reason: Optional[str] = None
    """The reason the agentic user was deleted (e.g. ``UserSoftDelete``, ``UserHardDelete``)."""


class AgenticUserUndeletedValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserUndeleted`` event."""

    event_type: Literal["agenticUserUndeleted"] = "agenticUserUndeleted"


class AgenticUserWorkloadOnboardingUpdatedValue(AgentLifecycleValueBase):
    """Payload for the ``agenticUserWorkloadOnboardingUpdated`` event."""

    event_type: Literal["agenticUserWorkloadOnboardingUpdated"] = "agenticUserWorkloadOnboardingUpdated"

    workload_name: Optional[str] = None
    """The workload being onboarded (e.g. ``Teams``)."""

    workload_onboarding_state: Optional[str] = None
    """The onboarding state for the workload (e.g. ``succeeded``)."""


__all__ = [
    "AgentLifecycleManager",
    "AgentLifecycleManagerRef",
    "AgentLifecycleUpdatedProperty",
    "AgentLifecycleValueBase",
    "AgenticUserIdentityCreatedValue",
    "AgenticUserIdentityUpdatedValue",
    "AgenticUserManagerUpdatedValue",
    "AgenticUserEnabledValue",
    "AgenticUserDisabledValue",
    "AgenticUserDeletedValue",
    "AgenticUserUndeletedValue",
    "AgenticUserWorkloadOnboardingUpdatedValue",
]
