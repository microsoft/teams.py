"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from dataclasses import dataclass
from typing import TypeAlias


@dataclass(frozen=True)
class AgenticUser:
    """Identifies an Agent ID user-shaped identity and its backing agent app."""

    agentic_app_instance_id: str
    agentic_user_id: str
    tenant_id: str | None = None
    agentic_blueprint_id: str | None = None


# AgenticIdentity is the SDK operation/request scope: the agentic program or
# identity used to authenticate proactive/API calls. It is intentionally modeled
# as an alias/union concept so it can grow to include concrete identities such as
# AgenticBlueprint, AgenticAppInstance, and AgenticUser without replacing the
# concrete activity-facing AgenticUser model.
AgenticIdentity: TypeAlias = AgenticUser


__all__ = ["AgenticIdentity", "AgenticUser"]
